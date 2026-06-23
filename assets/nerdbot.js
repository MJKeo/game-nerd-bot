() => {
    const setWelcomeLoading = (loading) => {
        window.__nerdbotWelcomeLoading = Boolean(loading);
        document.body?.classList.toggle(
            "nerdbot-welcome-loading",
            Boolean(loading)
        );
    };

    window.__nerdbotSetWelcomeLoading = setWelcomeLoading;

    if (!window.__nerdbotWelcomeGuardInstalled) {
        window.__nerdbotWelcomeGuardInstalled = true;

        const shouldBlockSend = () => window.__nerdbotWelcomeLoading === true;
        const isTextbox = (target) =>
            target instanceof HTMLTextAreaElement ||
            target instanceof HTMLInputElement;

        const blockEnterSubmit = (event) => {
            if (!shouldBlockSend() || event.key !== "Enter") {
                return;
            }

            if (!isTextbox(event.target) || event.target.dataset.testid !== "textbox") {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
        };

        const blockButtonSubmit = (event) => {
            if (!shouldBlockSend()) {
                return;
            }

            const target = event.target instanceof Element ? event.target : null;
            if (!target?.closest("button.submit-button")) {
                return;
            }

            event.preventDefault();
            event.stopImmediatePropagation();
        };

        document.addEventListener("keydown", blockEnterSubmit, true);
        document.addEventListener("keypress", blockEnterSubmit, true);
        document.addEventListener("click", blockButtonSubmit, true);
    }

    setWelcomeLoading(true);
}
