'use strict';

const contexts = [
  'background-image: radial-gradient(at <position>, red, blue)',
  'background-position: <position>',
  'object-position: <position>',
  'perspective-origin: <position>',
  'shape-outside: circle(at <position>)',
];

const values = [
  '10%',
  '20% 30px',
  '30px center',
  '40px top',
  'bottom 10% right 20%',
  'bottom right',
  'center',
  'center 50px',
  'center bottom',
  'center center',
  'center left',
  'left',
  'left bottom',
  'left center',
  'right 30% top 60px',
  'right 40%',
  'top',
  'top center',
];

function resultName(contextIndex, valueIndex) {
  return 'result_' + contextIndex + '_' + valueIndex;
}
