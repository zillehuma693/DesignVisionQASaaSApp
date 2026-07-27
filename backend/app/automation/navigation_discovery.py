from dataclasses import dataclass

from playwright.async_api import Page

DESTRUCTIVE_KEYWORDS = [
    "delete", "remove", "archive", "permanently", "deactivate",
    "cancel subscription", "unsubscribe", "destroy", "purge", "erase",
    "terminate", "revoke", "disconnect account",
]

_FIND_ELEMENTS_JS = """
() => {
    function cssPath(el) {
        if (el.id) return '#' + CSS.escape(el.id);
        const parts = [];
        let node = el;
        for (let depth = 0; depth < 6 && node && node.nodeType === 1 && node.tagName !== 'BODY'; depth++) {
            let part = node.tagName.toLowerCase();
            const parent = node.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(c => c.tagName === node.tagName);
                if (siblings.length > 1) {
                    part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
                }
            }
            parts.unshift(part);
            node = parent;
        }
        return parts.join(' > ');
    }

    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return false;
        const style = getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) return false;
        return true;
    }

    function classify(el, rect) {
        if (el.closest('nav, aside, header, [role="navigation"]')) return 'nav';
        if (el.closest('[role="tab"], [role="tablist"]') || el.getAttribute('role') === 'tab') return 'tab';
        if (el.closest('[role="menu"], [role="menuitem"]') || el.getAttribute('role') === 'menuitem') return 'dropdown';
        const style = getComputedStyle(el);
        if ((style.position === 'fixed' || style.position === 'absolute') &&
            rect.width < 80 && rect.height < 80 &&
            rect.right > window.innerWidth - 120 && rect.bottom > window.innerHeight - 120) {
            return 'fab';
        }
        if (el.closest('[class*="card"], article')) return 'card';
        if (el.tagName === 'A' && el.getAttribute('href')) return 'link';
        return 'button';
    }

    const candidates = new Set();
    const selectors = [
        'nav a', 'nav button', 'aside a', 'aside button', 'header a', 'header button',
        '[role="tab"]', '[role="menuitem"]', '[role="button"]',
        'button', 'a[href]', 'summary', '[aria-expanded]',
    ];
    for (const sel of selectors) {
        document.querySelectorAll(sel).forEach(el => candidates.add(el));
    }

    // Fallback: many real-world sidebars/menus use plain <div>/<span> rows with
    // an onClick handler instead of <a>/<button>/role. Catch the outermost
    // cursor-pointer element within nav-like containers (not every nested
    // icon/span inside it) so those still get discovered.
    const navLikeContainers = document.querySelectorAll(
        'nav, aside, header, [role="navigation"], [class*="sidebar" i], [class*="menu" i]'
    );
    for (const container of navLikeContainers) {
        const all = container.querySelectorAll('*');
        for (const el of all) {
            if (candidates.has(el)) continue;
            if (getComputedStyle(el).cursor !== 'pointer') continue;
            const parent = el.parentElement;
            if (parent && container.contains(parent) && getComputedStyle(parent).cursor === 'pointer') continue;
            candidates.add(el);
        }
    }

    const results = [];
    const seen = new Set();
    for (const el of candidates) {
        if (el.disabled) continue;
        if (!isVisible(el)) continue;
        const selector = cssPath(el);
        if (seen.has(selector)) continue;
        seen.add(selector);
        const rect = el.getBoundingClientRect();
        results.push({
            selector,
            text: (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 120),
            ariaLabel: el.getAttribute('aria-label') || '',
            kind: classify(el, rect),
        });
        if (results.length >= 80) break;
    }
    return results;
}
"""


@dataclass
class ActionableElement:
    selector: str
    text: str
    kind: str
    is_destructive: bool


def _is_destructive(*texts: str) -> bool:
    for text in texts:
        lowered = text.lower()
        if any(keyword in lowered for keyword in DESTRUCTIVE_KEYWORDS):
            return True
    return False


class NavigationDiscovery:
    async def find_actionable_elements(self, page: Page) -> list[ActionableElement]:
        try:
            raw = await page.evaluate(_FIND_ELEMENTS_JS)
        except Exception:
            return []

        elements = []
        for item in raw:
            text = (item.get("text") or "").strip()
            aria_label = (item.get("ariaLabel") or "").strip()
            elements.append(ActionableElement(
                selector=item["selector"],
                text=text or aria_label or "(unlabeled)",
                kind=item.get("kind", "button"),
                is_destructive=_is_destructive(text, aria_label),
            ))
        return elements
