() => {
    window.__nerdbotSetWelcomeLoading?.(false);
    window.__nerdbotWelcomeLoading = false;
    document.body?.classList.remove("nerdbot-welcome-loading");
    return [];
}
