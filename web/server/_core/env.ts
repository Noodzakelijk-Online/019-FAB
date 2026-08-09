export const ENV = {
  appId: process.env.VITE_APP_ID ?? "",
  cookieSecret: process.env.JWT_SECRET ?? "",
  databaseUrl: process.env.DATABASE_URL ?? "",
  oAuthServerUrl: process.env.OAUTH_SERVER_URL ?? "",
  ownerOpenId: process.env.OWNER_OPEN_ID ?? "",
  isProduction: process.env.NODE_ENV === "production",
  forgeApiUrl: process.env.BUILT_IN_FORGE_API_URL ?? "",
  forgeApiKey: process.env.BUILT_IN_FORGE_API_KEY ?? "",
  fabOperationsServiceToken: process.env.FAB_OPERATIONS_SERVICE_TOKEN ?? "",
  fabBillingEnabled: process.env.FAB_BILLING_ENABLED
    ? ["1", "true", "yes", "on"].includes(process.env.FAB_BILLING_ENABLED.toLowerCase())
    : process.env.NODE_ENV === "test",
  fabLocalApiUrl: process.env.FAB_LOCAL_API_URL ?? "http://127.0.0.1:5001",
  fabLocalApiToken: process.env.FAB_LOCAL_API_TOKEN ?? "",
  fabInstanceRoot: process.env.FAB_INSTANCE_ROOT ?? "",
  fabLocalApiInsecureHosts: (process.env.FAB_LOCAL_API_INSECURE_HOSTS ?? "")
    .split(",")
    .map(value => value.trim().toLowerCase())
    .filter(Boolean),
  fabWebHost: process.env.FAB_WEB_HOST ?? (process.env.NODE_ENV === "development" ? "127.0.0.1" : "0.0.0.0"),
  fabOperatorTrustedProxyAddresses: (process.env.FAB_OPERATOR_TRUSTED_PROXY_ADDRESSES ?? "")
    .split(",")
    .map(value => value.trim().toLowerCase())
    .filter(Boolean),
  fabOperatorTrustDockerGateway: process.env.FAB_OPERATOR_TRUST_DOCKER_GATEWAY
    ?.toLowerCase() === "true",
  fabOperatorLocalMode: process.env.FAB_OPERATOR_LOCAL_MODE
    ? ["1", "true", "yes", "on"].includes(process.env.FAB_OPERATOR_LOCAL_MODE.toLowerCase())
    : process.env.NODE_ENV === "development",
};
