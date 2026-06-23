() => {
    window.__nerdbotSetWelcomeLoading?.(true);
    window.__nerdbotWelcomeLoading = true;
    document.body?.classList.add("nerdbot-welcome-loading");
    return [];
}
