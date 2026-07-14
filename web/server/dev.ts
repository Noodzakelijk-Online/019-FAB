process.env.NODE_ENV ??= "development";

async function startDevelopmentServer() {
  await import("./_core/index");
}

void startDevelopmentServer();
