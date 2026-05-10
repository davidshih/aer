const fs = require('fs');
const path = require('path');
const { Resvg } = require('@resvg/resvg-js');

const svgPath = path.join(__dirname, '..', 'assets', 'icon.svg');
const pngPath = path.join(__dirname, '..', 'assets', 'icon.png');

const svg = fs.readFileSync(svgPath);
const resvg = new Resvg(svg, { fitTo: { mode: 'width', value: 128 } });
fs.writeFileSync(pngPath, resvg.render().asPng());
console.log(`wrote ${pngPath}`);
