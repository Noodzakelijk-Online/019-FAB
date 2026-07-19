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
  fabLocalApiUrl: process.env.FAB_LOCAL_API_URL ?? "http://127.0.0.1:5001",
  fabLocalApiToken: process.env.FAB_LOCAL_API_TOKEN ?? "",
  fabWebHost: process.env.FAB_WEB_HOST ?? (process.env.NODE_ENV === "development" ? "127.0.0.1" : "0.0.0.0"),
  fabOperatorLocalMode: process.env.FAB_OPERATOR_LOCAL_MODE
    ? ["1", "true", "yes", "on"].includes(process.env.FAB_OPERATOR_LOCAL_MODE.toLowerCase())
    : process.env.NODE_ENV === "development",
};
