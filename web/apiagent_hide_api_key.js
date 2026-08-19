import { app } from "../../scripts/app.js";

const API_CONFIG_NODE = "APIAgent_OpenAIAPIConfig";
const API_KEY_WIDGET = "API密钥";
const API_KEY_BUTTON_TEXT = "Get OpenAI API Key";

function isApiConfigNode(node) {
    return (
        node?.comfyClass === API_CONFIG_NODE ||
        node?.constructor?.comfyClass === API_CONFIG_NODE ||
        node?.type === API_CONFIG_NODE
    );
}

function maskValue(value) {
    if (!value) {
        return "";
    }
    const length = String(value).length;
    return "•".repeat(Math.min(16, Math.max(8, length)));
}

function forcePasswordInput(widget) {
    const candidates = [
        widget?.inputEl,
        widget?.element,
        widget?.element?.querySelector?.("input"),
    ].filter(Boolean);

    for (const element of candidates) {
        if (element?.tagName === "INPUT" || element?.type !== undefined) {
            element.type = "password";
            element.autocomplete = "off";
        }
    }
}

function isApiKeyButtonWidget(widget) {
    const fields = [widget?.name, widget?.label, widget?.value, widget?.text].map((value) => String(value || ""));
    return fields.some((value) => value.includes(API_KEY_BUTTON_TEXT));
}

function removeApiKeyButtonWidgets(node) {
    if (!node?.widgets?.length) {
        return;
    }
    node.widgets = node.widgets.filter((widget) => !isApiKeyButtonWidget(widget));
}

function hideApiKeyButtonElements() {
    const elements = document.querySelectorAll("button, a, input[type='button'], input[type='submit']");
    for (const element of elements) {
        const text = element.value || element.textContent || element.title || element.getAttribute("aria-label") || "";
        if (String(text).includes(API_KEY_BUTTON_TEXT)) {
            element.style.display = "none";
            element.hidden = true;
        }
    }
}

function patchWidget(widget) {
    if (!widget || widget.name !== API_KEY_WIDGET || widget.__apiagentPasswordPatched) {
        return;
    }

    widget.__apiagentPasswordPatched = true;
    widget.type = "password";
    widget.inputType = "password";
    widget.options = widget.options || {};
    widget.options.password = true;
    widget.options.secure = true;

    const originalCallback = widget.callback;
    widget.callback = function (...args) {
        forcePasswordInput(widget);
        return originalCallback?.apply(this, args);
    };

    if (typeof widget.draw === "function") {
        const originalDraw = widget.draw;
        widget.draw = function (...args) {
            const originalValue = this.value;
            if (originalValue) {
                this.value = maskValue(originalValue);
            }
            try {
                return originalDraw.apply(this, args);
            } finally {
                this.value = originalValue;
            }
        };
    }

    forcePasswordInput(widget);
    requestAnimationFrame(() => forcePasswordInput(widget));
}

function patchNode(node) {
    removeApiKeyButtonWidgets(node);

    if (!node.__apiagentAddWidgetPatched && typeof node.addWidget === "function") {
        node.__apiagentAddWidgetPatched = true;
        const originalAddWidget = node.addWidget;
        node.addWidget = function (...args) {
            const candidate = { type: args[0], name: args[1], value: args[2] };
            if (isApiKeyButtonWidget(candidate)) {
                return null;
            }
            const widget = originalAddWidget.apply(this, args);
            if (isApiKeyButtonWidget(widget)) {
                removeApiKeyButtonWidgets(this);
                return null;
            }
            patchWidget(widget);
            return widget;
        };
    }

    for (const widget of node.widgets || []) {
        patchWidget(widget);
    }

    hideApiKeyButtonElements();
    requestAnimationFrame(() => {
        removeApiKeyButtonWidgets(node);
        hideApiKeyButtonElements();
    });
    setTimeout(() => {
        removeApiKeyButtonWidgets(node);
        hideApiKeyButtonElements();
    }, 250);
}

app.registerExtension({
    name: "APIAgent.HideApiKey",
    nodeCreated(node) {
        if (!isApiConfigNode(node)) {
            return;
        }

        patchNode(node);

        const originalOnConfigure = node.onConfigure;
        node.onConfigure = function (...args) {
            const result = originalOnConfigure?.apply(this, args);
            patchNode(this);
            return result;
        };
    },
});
