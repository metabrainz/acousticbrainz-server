module.exports = {
  env: {
    browser: true,
    es6: true,
  },
  extends: [
    "plugin:react/recommended",
    "airbnb",
    "prettier",
    "prettier/@typescript-eslint",
    "prettier/react",
  ],
  globals: {
    Atomics: "readonly",
    SharedArrayBuffer: "readonly",
    JSX: true,
    "$": true
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
    },
    ecmaVersion: 2018,
    sourceType: "module",
  },
  plugins: ["react", "@typescript-eslint", "prettier"],
  rules: {
    "react/destructuring-assignment": "off",
    "react/prop-tyes": "off",
    "react/jsx-filename-extension": "off",
    "react/jsx-props-no-spreading": "off",
    "react/no-did-update-set-state": "off",
    "import/extensions": "off",
    "no-unused-vars": "off",
    camelcase: "off",
    "prettier/prettier": "warn",
    "lines-between-class-members": [
      "error",
      "always",
      { exceptAfterSingleLine: true },
    ],
    "jsx-a11y/label-has-associated-control": ['error', {
      "assert":"either"
    }],
    "react/static-property-placement": ["error", "static public field"],
    // We use console messages for some debugging, which is still required for now
    "no-console": "off",
    // we use alert for some messages
    "no-alert": "off",
    "no-restricted-globals": "off",
    // Some files have private methods which start with _
    "no-underscore-dangle": "off",
    // https://github.com/typescript-eslint/typescript-eslint/blob/master/packages/eslint-plugin/docs/rules/no-use-before-define.md#how-to-use
    "no-use-before-define": "off",
    "@typescript-eslint/no-use-before-define": ["error"],
    // We group multiple classes that implement a single functionality together
    "max-classes-per-file": "off",
    // Table columns without a title
    "jsx-a11y/control-has-associated-label": "off",
    // TODO: <a> tags without an href, until we add in proper routing
    "jsx-a11y/anchor-is-valid": "off",
    "no-plusplus": ["error", { "allowForLoopAfterthoughts": true }],
    // TODO: disable default on switch until we use enums
    "default-case": "off"
  },
  settings: {
    "import/resolver": {
      node: {
        extensions: [".js", ".jsx", ".ts", ".tsx"],
      },
    },
  },
  overrides: [
    {
      files: ["**/*.test.js", "**/*.test.ts", "**/*.test.tsx"],
      env: {
        jest: true,
      },
      plugins: ["jest"],
      rules: {
        "import/no-extraneous-dependencies": "off",
        "jest/no-disabled-tests": "warn",
        "jest/no-focused-tests": "error",
        "jest/no-identical-title": "error",
        "jest/prefer-to-have-length": "warn",
        "jest/valid-expect": "error",
      },
    },
  ],
};
