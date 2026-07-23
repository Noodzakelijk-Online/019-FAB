import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  AlertCircle,
  ArrowUpRight,
  Building2,
  CheckCircle2,
  KeyRound,
  Landmark,
  Loader2,
  RefreshCw,
  Save,
  ShieldCheck,
  Unplug,
  X,
} from "lucide-react";
import { useFabLocale } from "./fabLocale";
import { bool, text, type FabRecord } from "./fabView";

const WAVE_TOKEN_GUIDE_URL = "https://developer.waveapps.com/hc/en-us/articles/360020596571-Permitted-Use-Wave-Business-Owners";
const WAVE_SCOPE_GUIDE_URL = "https://developer.waveapps.com/hc/en-us/articles/360032818132-OAuth-Scopes";

export type FabWaveSetupSaveInput = {
  targetSystem?: "waveapps_business" | "waveapps_personal";
  accessToken?: string;
  businessId?: string;
  anchorAccountId?: string;
  defaultCategoryAccountId?: string;
  categoryAccountIds?: Record<string, string>;
  clearAccessToken?: boolean;
};

type FabWaveSetupDrawerProps = {
  open: boolean;
  connected: boolean;
  setup: FabRecord;
  busy: boolean;
  onClose: () => void;
  onSave: (input: FabWaveSetupSaveInput) => Promise<void>;
  onValidate: () => Promise<void>;
  onRefresh: () => Promise<void> | void;
};

export function FabWaveSetupDrawer({
  open,
  connected,
  setup,
  busy,
  onClose,
  onSave,
  onValidate,
  onRefresh,
}: FabWaveSetupDrawerProps) {
  const { copy, status: localizedStatus } = useFabLocale();
  const [accessToken, setAccessToken] = useState("");
  const [businessId, setBusinessId] = useState("");
  const [anchorAccountId, setAnchorAccountId] = useState("");
  const [defaultCategoryAccountId, setDefaultCategoryAccountId] = useState("");
  const [categoryAccountIds, setCategoryAccountIds] = useState<Record<string, string>>({});
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [error, setError] = useState("");
  const closeRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const mapping = record(setup.mapping);
  const anchorMapping = record(mapping.anchorAccount);
  const defaultMapping = record(mapping.defaultCategoryAccount);
  const configuredCategoryMappings = records(mapping.categoryAccounts);
  const accountOptions = record(setup.accountOptions);
  const anchorOptions = records(accountOptions.anchor);
  const expenseOptions = records(accountOptions.expense);
  const tokenConfigured = bool(setup.accessTokenConfigured);
  const validated = records(setup.accounts).length > 0 && Boolean(setup.lastValidatedAt);
  const mappingVerified = bool(mapping.verified);
  const ready = bool(setup.ready);
  const environmentOverrides = record(setup.environmentOverrides);
  const tokenEnvironmentOverride = bool(environmentOverrides.accessToken);
  const storage = record(setup.storage);
  const lastValidatedAt = text(setup.lastValidatedAt, "");
  const setupError = text(setup.error, "");
  const keyProtector = text(storage.keyProtector, "");
  const configuredCategoryKey = configuredCategoryMappings
    .map((row) => `${text(row.category)}:${text(row.accountId)}`)
    .sort()
    .join("|");
  const expenseOptionsKey = expenseOptions
    .map((account) => `${text(account.name)}:${text(account.id)}`)
    .sort()
    .join("|");
  const selectedCategoryCount = Object.keys(categoryAccountIds).length;
  const allExpenseCategoriesSelected = expenseOptions.length > 0 && expenseOptions.every((account) => {
    const name = text(account.name);
    return Boolean(name) && categoryAccountIds[name] === text(account.id);
  });

  useEffect(() => {
    if (!open) return;
    setAccessToken("");
    setBusinessId(text(setup.businessId, ""));
    setAnchorAccountId(text(anchorMapping.accountId, ""));
    setDefaultCategoryAccountId(text(defaultMapping.accountId, ""));
    const configuredCategories = Object.fromEntries(configuredCategoryMappings.flatMap((row) => {
      const category = text(row.category);
      const accountId = text(row.accountId);
      return category && accountId ? [[category, accountId]] : [];
    }));
    setCategoryAccountIds(Object.keys(configuredCategories).length
      ? configuredCategories
      : expenseCategoryMap(expenseOptions));
    setConfirmDisconnect(false);
    setError("");
  }, [open, setup.businessId, anchorMapping.accountId, defaultMapping.accountId, configuredCategoryKey, expenseOptionsKey]);

  useEffect(() => {
    if (!open) return;
    restoreFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    document.body.classList.add("fab-dialog-open");
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
      if (event.key !== "Tab") return;
      const dialog = closeRef.current?.closest<HTMLElement>("[role=dialog]");
      const focusable = dialog ? Array.from(dialog.querySelectorAll<HTMLElement>("a, button:not(:disabled), input:not(:disabled), select:not(:disabled)")) : [];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("fab-dialog-open");
      restoreFocusRef.current?.focus();
    };
  }, [busy, onClose, open]);

  if (!open) return null;

  async function saveConnection() {
    const normalizedBusinessId = businessId.trim();
    const normalizedToken = accessToken.trim();
    if (!normalizedBusinessId) {
      setError(copy("Enter the Wave business ID.", "Voer het Wave-bedrijfs-ID in."));
      return;
    }
    if (!tokenConfigured && !normalizedToken) {
      setError(copy("Enter a user-owned Wave access token.", "Voer een Wave-toegangstoken van de gebruiker in."));
      return;
    }
    setError("");
    try {
      await onSave({
        targetSystem: "waveapps_business",
        businessId: normalizedBusinessId,
        ...(normalizedToken ? { accessToken: normalizedToken } : {}),
      });
      setAccessToken("");
    } catch (cause) {
      setError(errorMessage(cause, copy("Wave connection could not be saved.", "Wave-koppeling kon niet worden opgeslagen.")));
    }
  }

  async function validateConnection() {
    setError("");
    try {
      await onValidate();
    } catch (cause) {
      setError(errorMessage(cause, copy("Wave validation failed.", "Wave-validatie is mislukt.")));
    }
  }

  async function saveMapping() {
    if (!anchorAccountId || !defaultCategoryAccountId || selectedCategoryCount === 0) {
      setError(copy("Select a funding account, a fallback expense account, and at least one explicit expense category.", "Selecteer een betaalrekening, een standaardkostenrekening en minimaal een expliciete kostencategorie."));
      return;
    }
    setError("");
    try {
      await onSave({
        targetSystem: "waveapps_business",
        anchorAccountId,
        defaultCategoryAccountId,
        categoryAccountIds,
      });
    } catch (cause) {
      setError(errorMessage(cause, copy("Wave account mapping could not be saved.", "Wave-rekeningtoewijzing kon niet worden opgeslagen.")));
    }
  }

  function toggleExpenseCategory(account: FabRecord) {
    const category = text(account.name);
    const accountId = text(account.id);
    if (!category || !accountId) return;
    setCategoryAccountIds((current) => {
      const next = { ...current };
      if (next[category] === accountId) delete next[category];
      else next[category] = accountId;
      return next;
    });
  }

  async function disconnect() {
    if (!confirmDisconnect || tokenEnvironmentOverride) return;
    setError("");
    try {
      await onSave({ targetSystem: "waveapps_business", clearAccessToken: true });
      setConfirmDisconnect(false);
      setAccessToken("");
    } catch (cause) {
      setError(errorMessage(cause, copy("Wave could not be disconnected.", "Wave kon niet worden losgekoppeld.")));
    }
  }

  return createPortal(
    <div className="fab-command-overlay" role="presentation" onMouseDown={(event) => { if (!busy && event.target === event.currentTarget) onClose(); }}>
      <aside className="fab-detail-drawer fab-wave-setup-drawer" role="dialog" aria-modal="true" aria-labelledby="fab-wave-setup-title" aria-describedby="fab-wave-setup-description">
        <div className="fab-command-header">
          <div><span>{copy("Downstream ledger", "Vervolggrootboek")}</span><h2 id="fab-wave-setup-title">Wave - Noodzakelijk Online</h2></div>
          <button ref={closeRef} className="fab-icon-button" onClick={onClose} disabled={busy} aria-label={copy("Close Wave setup", "Wave-instellingen sluiten")} title={copy("Close Wave setup", "Wave-instellingen sluiten")}><X aria-hidden="true" /></button>
        </div>
        <div className="fab-detail-body">
          <p id="fab-wave-setup-description">{copy("Connect FAB to the Wave GraphQL API, verify the selected business, and map only accounts returned by its live chart of accounts.", "Koppel FAB aan de Wave GraphQL-API, verifieer het geselecteerde bedrijf en wijs alleen rekeningen toe die in het actuele rekeningschema staan.")}</p>

          <div className="fab-wave-status-line">
            <span className={`fab-status-chip tone-${ready ? "good" : "warn"}`}>{localizedStatus(text(setup.status, "needs_token"))}</span>
            <small>{lastValidatedAt ? `${copy("Last validated", "Laatst gevalideerd")}: ${new Date(lastValidatedAt).toLocaleString()}` : copy("Not validated yet", "Nog niet gevalideerd")}</small>
          </div>

          <div className="fab-drive-setup-progress">
            <SetupStep complete={tokenConfigured && Boolean(text(setup.businessId))} icon={KeyRound} title={copy("Secure API connection", "Beveiligde API-koppeling")} detail={tokenConfigured ? copy("Token stored without browser exposure", "Token opgeslagen zonder browserweergave") : copy("Token and business ID required", "Token en bedrijfs-ID vereist")} />
            <SetupStep complete={validated} icon={Building2} title={copy("Business validation", "Bedrijfsvalidatie")} detail={validated ? `${records(setup.accounts).length} ${copy("accounts loaded", "rekeningen geladen")}` : copy("Live account read required", "Actuele rekeningcontrole vereist")} />
            <SetupStep complete={mappingVerified} icon={Landmark} title={copy("Posting account mapping", "Toewijzing boekingsrekeningen")} detail={mappingVerified ? `${configuredCategoryMappings.length} ${copy("explicit categories verified", "expliciete categorieen gevalideerd")}` : copy("Funding, fallback, and explicit expense categories required", "Betaalrekening, standaardrekening en expliciete kostencategorieen vereist")} />
          </div>

          <section className="fab-drive-credential-panel">
            <div className="fab-subsection-heading"><div><span>{copy("Step 1", "Stap 1")}</span><h3>{copy("Store the Wave connection", "Wave-koppeling opslaan")}</h3></div></div>
            <div className="fab-wave-token-guide">
              <div>
                <strong>{copy("Create your Wave access token", "Maak je Wave-toegangstoken")}</strong>
                <span>{copy("For your own Wave business, create an application in Wave's Developer Portal and generate its long-lived access token. FAB never reads your Wave password or browser session.", "Maak voor je eigen Wave-bedrijf een toepassing in het Wave Developer Portal en genereer daar het langlopende toegangstoken. FAB leest nooit je Wave-wachtwoord of browsersessie.")}</span>
              </div>
              <a href={WAVE_TOKEN_GUIDE_URL} target="_blank" rel="noreferrer">{copy("Open official token guide", "Open officiele tokenhandleiding")} <ArrowUpRight aria-hidden="true" /></a>
              <small>{copy("For OAuth applications, current FAB workflows need business:read, account:read, customer:read, product:read, invoice:read, and transaction:write. Validation is read-only; posting remains approval-gated.", "Huidige FAB-workflows vereisen voor OAuth-toepassingen business:read, account:read, customer:read, product:read, invoice:read en transaction:write. Validatie is alleen-lezen; boeken blijft goedkeuringsplichtig.")} <a href={WAVE_SCOPE_GUIDE_URL} target="_blank" rel="noreferrer">{copy("Review scopes", "Bekijk scopes")} <ArrowUpRight aria-hidden="true" /></a></small>
            </div>
            <form className="fab-wave-form" onSubmit={(event) => { event.preventDefault(); void saveConnection(); }}>
              <label><span>{copy("Wave business ID", "Wave-bedrijfs-ID")}</span><input value={businessId} onChange={(event) => setBusinessId(event.target.value)} autoComplete="off" spellCheck={false} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" disabled={busy || bool(environmentOverrides.businessId)} /></label>
              <label><span>{tokenConfigured ? copy("Replace access token", "Toegangstoken vervangen") : copy("Access token", "Toegangstoken")}</span><input type="password" value={accessToken} onChange={(event) => setAccessToken(event.target.value)} autoComplete="new-password" spellCheck={false} placeholder={tokenConfigured ? copy("Leave blank to keep the stored token", "Laat leeg om het opgeslagen token te behouden") : copy("Paste the user-owned Wave token", "Plak het Wave-token van de gebruiker")} disabled={busy || tokenEnvironmentOverride} /></label>
              <button className="fab-primary-button" type="submit" disabled={!connected || busy || (!businessId.trim()) || (!tokenConfigured && !accessToken.trim())}>{busy ? <Loader2 className="is-spinning" aria-hidden="true" /> : <Save aria-hidden="true" />} {copy("Save connection", "Koppeling opslaan")}</button>
            </form>
          </section>

          <section className="fab-drive-credential-panel">
            <div className="fab-subsection-heading"><div><span>{copy("Step 2", "Stap 2")}</span><h3>{copy("Validate business and accounts", "Bedrijf en rekeningen valideren")}</h3></div></div>
            <p>{copy("FAB performs a read-only account discovery. It does not create or modify Wave records during validation.", "FAB voert een alleen-lezen rekeningcontrole uit. Tijdens validatie worden geen Wave-records gemaakt of gewijzigd.")}</p>
            <div className="fab-detail-actions">
              <button className="fab-primary-button" type="button" onClick={() => { void validateConnection(); }} disabled={!connected || busy || !tokenConfigured || !text(setup.businessId, "")}>{busy ? <Loader2 className="is-spinning" aria-hidden="true" /> : <ShieldCheck aria-hidden="true" />} {copy("Validate Wave", "Wave valideren")}</button>
              <button className="fab-secondary-button" type="button" onClick={() => { void onRefresh(); }} disabled={busy}><RefreshCw aria-hidden="true" /> {copy("Refresh status", "Status vernieuwen")}</button>
            </div>
          </section>

          <section className="fab-drive-credential-panel">
            <div className="fab-subsection-heading"><div><span>{copy("Step 3", "Stap 3")}</span><h3>{copy("Map verified posting accounts", "Gevalideerde boekingsrekeningen toewijzen")}</h3></div></div>
            <form className="fab-wave-form" onSubmit={(event) => { event.preventDefault(); void saveMapping(); }}>
              <label><span>{copy("Funding account", "Betaalrekening")}</span><select value={anchorAccountId} onChange={(event) => setAnchorAccountId(event.target.value)} disabled={busy || !validated}><option value="">{copy("Select a verified Wave account", "Selecteer een gevalideerde Wave-rekening")}</option>{anchorOptions.map((account) => <option key={text(account.id)} value={text(account.id)}>{accountLabel(account)}</option>)}</select></label>
              <label><span>{copy("Default expense account", "Standaardkostenrekening")}</span><select value={defaultCategoryAccountId} onChange={(event) => setDefaultCategoryAccountId(event.target.value)} disabled={busy || !validated}><option value="">{copy("Select a verified Wave account", "Selecteer een gevalideerde Wave-rekening")}</option>{expenseOptions.map((account) => <option key={text(account.id)} value={text(account.id)}>{accountLabel(account)}</option>)}</select></label>
              <div className="fab-wave-category-map">
                <div className="fab-wave-category-map-heading">
                  <div><strong>{copy("Explicit expense categories", "Expliciete kostencategorieen")}</strong><small>{selectedCategoryCount} / {expenseOptions.length} {copy("selected from Wave", "geselecteerd uit Wave")}</small></div>
                  <button className="fab-secondary-button compact" type="button" disabled={busy || !validated || expenseOptions.length === 0} onClick={() => setCategoryAccountIds(allExpenseCategoriesSelected ? {} : expenseCategoryMap(expenseOptions))}>{allExpenseCategoriesSelected ? copy("Clear", "Wissen") : copy("Select all", "Alles selecteren")}</button>
                </div>
                <div className="fab-wave-category-list">
                  {expenseOptions.map((account) => {
                    const category = text(account.name);
                    const accountId = text(account.id);
                    const checked = Boolean(category) && categoryAccountIds[category] === accountId;
                    return <label className="fab-review-checkbox" key={accountId || category}><input type="checkbox" checked={checked} onChange={() => toggleExpenseCategory(account)} disabled={busy || !validated} /><span><strong>{category || accountId}</strong><small>{copy("Use this exact Wave account as a FAB review and posting category", "Gebruik deze exacte Wave-rekening als FAB-controle- en boekingscategorie")}</small></span></label>;
                  })}
                  {validated && expenseOptions.length === 0 && <p className="fab-inline-error">{copy("Wave returned no expense accounts. Add an expense account in Wave and validate again.", "Wave heeft geen kostenrekeningen teruggegeven. Voeg een kostenrekening toe in Wave en valideer opnieuw.")}</p>}
                </div>
              </div>
              <button className="fab-primary-button" type="submit" disabled={!connected || busy || !validated || !anchorAccountId || !defaultCategoryAccountId || selectedCategoryCount === 0}>{busy ? <Loader2 className="is-spinning" aria-hidden="true" /> : <Landmark aria-hidden="true" />} {copy("Save verified mapping", "Gevalideerde toewijzing opslaan")}</button>
            </form>
          </section>

          <div className="fab-drive-safety-note"><ShieldCheck aria-hidden="true" /><div><strong>{copy("Local credential protection", "Lokale referentiebeveiliging")}</strong><span>{copy("The Wave token is encrypted at rest and its encryption key is protected for the current Windows user.", "Het Wave-token is versleuteld opgeslagen en de sleutel is beveiligd voor de huidige Windows-gebruiker.")} {keyProtector ? `${copy("Protector", "Beveiliging")}: ${keyProtector}.` : ""}</span></div></div>

          {tokenConfigured && <section className="fab-wave-disconnect">
            <label className="fab-review-checkbox"><input type="checkbox" checked={confirmDisconnect} onChange={(event) => setConfirmDisconnect(event.target.checked)} disabled={busy || tokenEnvironmentOverride} /><span>{tokenEnvironmentOverride ? copy("The token is controlled by an environment override and cannot be removed here.", "Het token wordt beheerd via een omgevingsinstelling en kan hier niet worden verwijderd.") : copy("Confirm removal of the locally stored Wave access token", "Bevestig verwijdering van het lokaal opgeslagen Wave-toegangstoken")}</span></label>
            <button className="fab-secondary-button tone-bad" type="button" onClick={() => { void disconnect(); }} disabled={busy || !confirmDisconnect || tokenEnvironmentOverride}><Unplug aria-hidden="true" /> {copy("Disconnect Wave", "Wave loskoppelen")}</button>
          </section>}

          {!connected && <div className="fab-panel-state tone-bad" role="alert"><AlertCircle aria-hidden="true" /><div><strong>{copy("Local API disconnected", "Lokale API niet verbonden")}</strong><span>{copy("Wave setup requires the authoritative local FAB API.", "Wave-installatie vereist de gezaghebbende lokale FAB-API.")}</span></div></div>}
          {(error || setupError) && <div className="fab-inline-error" role="alert">{error || setupError}</div>}
        </div>
      </aside>
    </div>,
    document.body,
  );
}

type SetupStepProps = {
  complete: boolean;
  icon: typeof KeyRound;
  title: string;
  detail: string;
};

function SetupStep({ complete, icon: Icon, title, detail }: SetupStepProps) {
  return <div className={`fab-drive-setup-step tone-${complete ? "good" : "neutral"}`}><span>{complete ? <CheckCircle2 aria-hidden="true" /> : <Icon aria-hidden="true" />}</span><div><strong>{title}</strong><small>{detail}</small></div></div>;
}

function record(value: unknown): FabRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? value as FabRecord : {};
}

function records(value: unknown): FabRecord[] {
  return Array.isArray(value) ? value.flatMap((item) => Object.keys(record(item)).length ? [record(item)] : []) : [];
}

function accountLabel(account: FabRecord): string {
  const subtype = record(account.subtype);
  const detail = text(subtype.name, text(subtype.value));
  return detail ? `${text(account.name, text(account.id))} - ${detail}` : text(account.name, text(account.id));
}

function expenseCategoryMap(accounts: FabRecord[]): Record<string, string> {
  return Object.fromEntries(accounts.flatMap((account) => {
    const category = text(account.name);
    const accountId = text(account.id);
    return category && accountId ? [[category, accountId]] : [];
  }));
}

function errorMessage(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message ? cause.message : fallback;
}
