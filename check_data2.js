const fs = require('fs');
const content = fs.readFileSync('data/news-2026-08-19.js', 'utf8');

// Find the JSON part - starts after the window assignment
const jsonStart = content.indexOf('{"date"');
// Find end - the last }
let depth = 0;
let end = -1;
for (let i = content.length - 1; i >= 0; i--) {
  if (content[i] === '}') {
    if (depth === 0) { end = i + 1; }
    depth++;
  } else if (content[i] === '{') {
    depth--;
    if (depth === 0) { break; }
  }
}

const jsonStr = content.slice(jsonStart, end);
const data = JSON.parse(jsonStr);

console.log('=== ARTICLES ===');
data.articles.forEach((a, i) => {
  console.log(`\n${i + 1}. ${a.title.slice(0, 60)}`);
  const vp = a.vocabPoints || [];
  const sp = a.slangPoints || [];
  const gp = a.grammarPoints || [];
  console.log(`   vocab: ${vp.length}, grammar: ${gp.length}, slang: ${sp.length}`);
  if (vp.length > 0) {
    console.log('   VOCAB TERMS:', vp.map(v => v.term).join(', '));
  }
  if (sp.length > 0) {
    console.log('   SLANG TERMS:', sp.map(s => s.term + ' (' + s.meaning + ')').join(' | '));
  }
});
