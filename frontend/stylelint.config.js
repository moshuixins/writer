export default {
  extends: [
    'stylelint-config-standard-scss',
    'stylelint-config-standard-vue/scss',
    'stylelint-config-recess-order',
    '@stylistic/stylelint-config',
  ],
  plugins: [
    'stylelint-scss',
  ],
  rules: {
    'at-rule-no-unknown': null,
    'custom-property-empty-line-before': null,
    'font-family-no-missing-generic-family-keyword': null,
    'function-no-unknown': [
      true,
      {
        ignoreFunctions: [
          'v-bind',
          'map-get',
          'lighten',
          'darken',
        ],
      },
    ],
    'media-feature-range-notation': null,
    'no-descending-specificity': null,
    'property-no-unknown': null,
    'scss/double-slash-comment-empty-line-before': null,
    'scss/no-global-function-names': null,
    'selector-class-pattern': null,
    'selector-pseudo-class-no-unknown': [
      true,
      {
        ignorePseudoClasses: [
          'deep',
          'global',
          'slotted',
        ],
      },
    ],
    'selector-pseudo-element-no-unknown': [
      true,
      {
        ignorePseudoElements: [
          '/^view-transition/',
        ],
      },
    ],
    '@stylistic/block-closing-brace-newline-after': [
      'always',
      {
        ignoreAtRules: ['if', 'else'],
      },
    ],
    '@stylistic/max-line-length': null,
  },
  allowEmptyInput: true,
  ignoreFiles: [
    'node_modules/**/*',
    'dist*/**/*',
  ],
}
