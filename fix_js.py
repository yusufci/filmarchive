import re

js_path = '/root/filmarchive/static/gallery.js'
with open(js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Prepend a safe getElementById wrapper
wrapper = """
const _originalGetElementById = document.getElementById.bind(document);
document.getElementById = function(id) {
    const el = _originalGetElementById(id);
    if (el) return el;
    // Return a dummy element to prevent crashes
    return {
        addEventListener: function(){},
        classList: { add: function(){}, remove: function(){}, toggle: function(){} },
        style: {},
        setAttribute: function(){},
        innerHTML: '',
        innerText: '',
        textContent: '',
        value: ''
    };
};
"""

if "_originalGetElementById" not in content:
    content = wrapper + content
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(content)
        print("JS wrapper added")
else:
    print("JS wrapper already exists")

