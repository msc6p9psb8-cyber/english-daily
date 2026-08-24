const fs = require('fs');
const content = fs.readFileSync('data/news-2026-08-19.js', 'utf8');

// Find the JSON part
const jsonStart = content.indexOf('{"date"');
let depth = 0, end = -1;
for (let i = content.length - 1; i >= 0; i--) {
  if (content[i] === '}') { if (depth === 0) end = i + 1; depth++; }
  else if (content[i] === '{') { depth--; if (depth === 0) break; }
}
const data = JSON.parse(content.slice(jsonStart, end));

// Check vocabPoints structure
const a = data.articles[0];
console.log('=== VOCAB STRUCTURE ===');
console.log(JSON.stringify(a.vocabPoints, null, 2));
console.log('\n=== GRAMMAR STRUCTURE ===');
console.log(JSON.stringify(a.grammarPoints, null, 2));
console.log('\n=== SLANG STRUCTURE ===');
console.log(JSON.stringify(a.slangPoints, null, 2));

// Check if there's a different field name
console.log('\n=== ARTICLE KEYS ===');
console.log(Object.keys(a));
