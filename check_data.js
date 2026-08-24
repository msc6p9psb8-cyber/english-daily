const fs = require('fs');
const content = fs.readFileSync('data/news-2026-08-19.js', 'utf8');

// Extract JSON by finding the JSON object
const start = content.indexOf('{', content.indexOf('window.__LIVE_NEWS__'));
const end = content.lastIndexOf('}');
const jsonStr = content.slice(start, end + 1);

try {
  const data = JSON.parse(jsonStr);
  console.log('Articles count:', data.articles.length);
  data.articles.forEach((a, i) => {
    const vocab = a.vocabPoints ? a.vocabPoints.length : 0;
    const grammar = a.grammarPoints ? a.grammarPoints.length : 0;
    const slang = a.slangPoints ? a.slangPoints.length : 0;
    console.log(`${i + 1}. ${a.title.slice(0, 50)}...`);
    console.log(`   vocab: ${vocab}, grammar: ${grammar}, slang: ${slang}`);
  });
} catch (e) {
  console.log('Parse error:', e.message);
  console.log('Content length:', content.length);
}
