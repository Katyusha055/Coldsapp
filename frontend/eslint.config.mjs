import js from '@eslint/js';
import prettier from '@vue/eslint-config-prettier';
import vue from 'eslint-plugin-vue';
import globals from 'globals';

const storageGlobals = [
    { name: 'localStorage', message: 'Client data must not live in web storage (XSS risk).' },
    { name: 'sessionStorage', message: 'Client data must not live in web storage (XSS risk).' }
];

export default [
    {
        ignores: ['dist/**', 'public/**']
    },
    js.configs.recommended,
    ...vue.configs['flat/recommended'],
    prettier,
    {
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: globals.browser
        },
        rules: {
            'vue/multi-word-component-names': 'off',
            'vue/no-reserved-component-names': 'off',
            'vue/block-order': ['error', { order: ['script', 'template', 'style'] }],
            'vue/no-v-html': 'error',
            'vue/no-setup-props-reactivity-loss': 'error',
            'vue/no-unused-properties': 'error',
            'no-restricted-globals': ['error', ...storageGlobals, { name: 'fetch', message: 'Call the API through src/services.' }],
            'no-restricted-properties': [
                'error',
                { object: 'window', property: 'localStorage', message: 'Client data must not live in web storage (XSS risk).' },
                { object: 'window', property: 'sessionStorage', message: 'Client data must not live in web storage (XSS risk).' },
                { object: 'window', property: 'fetch', message: 'Call the API through src/services.' }
            ]
        }
    },
    {
        files: ['src/services/**'],
        rules: {
            'no-restricted-globals': ['error', ...storageGlobals],
            'no-restricted-properties': [
                'error',
                { object: 'window', property: 'localStorage', message: 'Client data must not live in web storage (XSS risk).' },
                { object: 'window', property: 'sessionStorage', message: 'Client data must not live in web storage (XSS risk).' }
            ]
        }
    },
    {
        files: ['*.config.{js,mjs,cjs}'],
        languageOptions: {
            globals: globals.node
        }
    }
];
