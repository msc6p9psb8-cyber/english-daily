#!/usr/bin/env python3
"""
Smart news injector with built-in vocabulary/grammar/slang bank.
Usage: python3 update_news.py news_data.json

Lightweight JSON input (automation only provides titles + summaries + topics):
[
  {
    "date": "2026-08-12",
    "source": "BBC",
    "country": "UK",
    "title": "UK Government Unveils Green Plan",
    "summary": "The UK government announced a sweeping green investment plan...",
    "url": "https://...",
    "topics": ["climate", "politics", "economy"]
  }
]

The script auto-matches 3 vocab + 1 grammar + 1 slang per article from its built-in bank.
Tracks usage to avoid repeating words across days.
"""
import json
import re
import sys
import os
import time
import random
import hashlib

# ── 结构自愈 & 权威基础词典 ─────────────────────────────
# base_dict.py 由 english-learning-workspace.html 的 HW_CORE 自动生成，
# 是"悬停释义"与"新闻词提取"共享的唯一事实来源（word -> 中文释义）。
# 任何出现在新闻正文中的常用词，只要在 base_dict 中，就能自动得到释义，
# 无需再逐个手工维护 —— 这就是"彻底解决悬停缺失"的结构性保证。
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    from base_dict import BASE_DICT as _BASE_DICT
except Exception:
    _BASE_DICT = {}

# 英文释义库 en_gloss.py（由 build_en_gloss.py 从 ECDICT 全量词典生成，
# 数千常用词的英文 gloss），供词汇点 en_def 字段使用。
try:
    from en_gloss import EN_GLOSS as _ECDICT_GLOSS
except Exception:
    _ECDICT_GLOSS = {}

# Prefer the local workspace file; fall back to index.html (GitHub repo layout)
HTML_FILE = os.path.join(_SCRIPT_DIR, "english-learning-workspace.html")
if not os.path.exists(HTML_FILE):
    HTML_FILE = os.path.join(_SCRIPT_DIR, "index.html")
TRACKER_FILE = os.path.join(_SCRIPT_DIR, ".news_tracker.json")

# ============================================================
# VOCABULARY BANK — 500+ words in 12 topic categories
# ============================================================
VOCAB_BANK = {
    "politics": [
        {"word":"legislation","phonetic":"/ˌledʒɪsˈleɪʃən/","definition":"立法；法规；laws made by a governing body","example":"The new legislation aims to reduce carbon emissions by 2035."},
        {"word":"bipartisan","phonetic":"/ˌbaɪˈpɑːrtɪzæn/","definition":"两党合作的；involving cooperation between two political parties","example":"The bill passed with rare bipartisan support."},
        {"word":"referendum","phonetic":"/ˌrefəˈrendəm/","definition":"全民公投；a direct vote by all citizens on a specific issue","example":"Scotland held a referendum on independence in 2014."},
        {"word":"diplomacy","phonetic":"/dɪˈpləʊməsi/","definition":"外交；the profession of managing international relations","example":"The crisis was resolved through quiet diplomacy."},
        {"word":"sovereignty","phonetic":"/ˈsɒvrənti/","definition":"主权；supreme power or authority over a territory","example":"The treaty recognizes the nation's sovereignty over the islands."},
        {"word":"coalition","phonetic":"/ˌkəʊəˈlɪʃən/","definition":"联盟；联合政府；a temporary alliance of political parties","example":"The coalition government faced its first major test."},
        {"word":"mandate","phonetic":"/ˈmændeɪt/","definition":"授权；选举赋予的权力；official authority to carry out a policy","example":"The party claimed a strong mandate for reform after the landslide victory."},
        {"word":"lobbying","phonetic":"/ˈlɒbiɪŋ/","definition":"游说；the activity of trying to influence politicians","example":"The tech industry spent millions on lobbying last year."},
        {"word":"impeachment","phonetic":"/ɪmˈpiːtʃmənt/","definition":"弹劾；a formal charge of misconduct against a public official","example":"The impeachment trial lasted three weeks in the Senate."},
        {"word":"filibuster","phonetic":"/ˈfɪlɪbʌstər/","definition":"阻挠议事；a prolonged speech to delay legislative action","example":"The senator launched a filibuster that lasted over 12 hours."},
        {"word":"incumbent","phonetic":"/ɪnˈkʌmbənt/","definition":"现任者；the current holder of a political office","example":"The incumbent leads in the polls by five points."},
        {"word":"ratify","phonetic":"/ˈrætɪfaɪ/","definition":"批准；正式签署生效；to formally approve and make official","example":"Parliament voted to ratify the international climate agreement."},
        {"word":"caucus","phonetic":"/ˈkɔːkəs/","definition":"党团会议；a meeting of party members to select candidates","example":"The Iowa caucus marked the start of primary season."},
        {"word":"gerrymandering","phonetic":"/ˈdʒerimændərɪŋ/","definition":"选区操纵；manipulating electoral boundaries for political advantage","example":"The court ruled the district map was a case of racial gerrymandering."},
        {"word":"decree","phonetic":"/dɪˈkriː/","definition":"法令；政令；an official order issued by a legal authority","example":"The president issued a decree banning the import of certain goods."},
    ],
    "economy": [
        {"word":"inflation","phonetic":"/ɪnˈfleɪʃən/","definition":"通货膨胀；a general increase in prices and fall in purchasing power","example":"Inflation reached a 40-year high of 9.1 percent."},
        {"word":"recession","phonetic":"/rɪˈseʃən/","definition":"经济衰退；a period of temporary economic decline","example":"Economists warned the country could slip into recession by year's end."},
        {"word":"subsidy","phonetic":"/ˈsʌbsɪdi/","definition":"补贴；政府资助；government financial support to an industry","example":"The government announced new subsidies for electric vehicle buyers."},
        {"word":"tariff","phonetic":"/ˈtærɪf/","definition":"关税；a tax on imported goods","example":"The new tariffs on steel imports raised tensions with trading partners."},
        {"word":"stimulus","phonetic":"/ˈstɪmjʊləs/","definition":"经济刺激措施；measures designed to boost economic activity","example":"The stimulus package included direct payments to households."},
        {"word":"deficit","phonetic":"/ˈdefɪsɪt/","definition":"赤字；the amount by which spending exceeds revenue","example":"The trade deficit widened to a record $68 billion."},
        {"word":"austerity","phonetic":"/ɒˈsterɪti/","definition":"紧缩政策；strict economic policies to reduce government debt","example":"Years of austerity led to cuts in public services."},
        {"word":"bullish","phonetic":"/ˈbʊlɪʃ/","definition":"看涨的；乐观的；confident about rising prices or positive outlook","example":"Analysts remain bullish on tech stocks despite volatility."},
        {"word":"volatility","phonetic":"/ˌvɒləˈtɪləti/","definition":"波动性；rapid and unpredictable changes in value","example":"Market volatility surged after the unexpected rate hike."},
        {"word":"liquidity","phonetic":"/lɪˈkwɪdəti/","definition":"流动性；the availability of liquid assets to a market","example":"The central bank injected liquidity to stabilize the banking sector."},
        {"word":"deregulation","phonetic":"/diːˌreɡjʊˈleɪʃən/","definition":"放松管制；removing government rules from an industry","example":"Financial deregulation was blamed for the 2008 crisis."},
        {"word":"monopoly","phonetic":"/məˈnɒpəli/","definition":"垄断；exclusive control of a commodity or service","example":"The company was fined for abusing its monopoly position."},
        {"word":"dividend","phonetic":"/ˈdɪvɪdend/","definition":"股息；红利；a sum of money paid to shareholders from profits","example":"The bank raised its quarterly dividend by 15 percent."},
        {"word":"foreclosure","phonetic":"/fɔːrˈkləʊʒər/","definition":"止赎；taking possession of a property when mortgage payments fail","example":"Foreclosure rates spiked during the housing crisis."},
        {"word":"entrepreneurship","phonetic":"/ˌɒntrəprəˈnɜːrʃɪp/","definition":"创业精神；the activity of setting up businesses","example":"The city has become a hub for tech entrepreneurship."},
    ],
    "tech_ai": [
        {"word":"algorithm","phonetic":"/ˈælɡərɪðəm/","definition":"算法；a set of rules for solving problems, especially by a computer","example":"The recommendation algorithm learns from your viewing history."},
        {"word":"automation","phonetic":"/ˌɔːtəˈmeɪʃən/","definition":"自动化；using machines to do work previously done by people","example":"Factory automation eliminated hundreds of assembly line jobs."},
        {"word":"cybersecurity","phonetic":"/ˌsaɪbərˈsekjʊrəti/","definition":"网络安全；measures taken to protect systems from digital attacks","example":"The company invested heavily in cybersecurity after the data breach."},
        {"word":"encryption","phonetic":"/ɪnˈkrɪpʃən/","definition":"加密；the process of converting data into a coded form","example":"End-to-end encryption ensures only the sender and recipient can read messages."},
        {"word":"bandwidth","phonetic":"/ˈbændwɪdθ/","definition":"带宽；网页容量；the maximum data transfer rate of a network","example":"The video call requires at least 5 Mbps of bandwidth."},
        {"word":"deployment","phonetic":"/dɪˈplɔɪmənt/","definition":"部署；发布；the act of putting software into production use","example":"The deployment of the new feature was delayed by testing."},
        {"word":"scalability","phonetic":"/ˌskeɪləˈbɪləti/","definition":"可扩展性；the capacity to handle growing amounts of work","example":"Cloud computing provides nearly unlimited scalability."},
        {"word":"open-source","phonetic":"/ˈəʊpən sɔːrs/","definition":"开源的；software with source code available for anyone to use","example":"Linux is the most successful open-source operating system."},
        {"word":"neural","phonetic":"/ˈnjʊərəl/","definition":"神经网络的；relating to computer systems modeled on the human brain","example":"Neural networks have revolutionized image recognition."},
        {"word":"interface","phonetic":"/ˈɪntərfeɪs/","definition":"接口；交互界面；a point where two systems meet and interact","example":"The voice interface makes the device accessible to visually impaired users."},
        {"word":"latency","phonetic":"/ˈleɪtənsi/","definition":"延迟；响应时间；the delay before data transfer begins","example":"5G networks promise latency under 10 milliseconds."},
        {"word":"blockchain","phonetic":"/ˈblɒktʃeɪn/","definition":"区块链；a decentralized digital ledger of transactions","example":"Blockchain technology underpins most cryptocurrencies."},
        {"word":"quantum","phonetic":"/ˈkwɒntəm/","definition":"量子；relating to computing using quantum mechanical phenomena","example":"Quantum computers could break current encryption methods."},
        {"word":"augmented","phonetic":"/ɔːɡˈmentɪd/","definition":"增强的；叠加数字信息到现实世界；enhanced by computer-generated input","example":"Augmented reality apps overlay directions onto your camera view."},
        {"word":"interoperability","phonetic":"/ˌɪntərɒpərəˈbɪləti/","definition":"互操作性；不同系统协同工作的能力；ability of systems to work together","example":"Interoperability remains a challenge between competing smart home platforms."},
    ],
    "climate": [
        {"word":"emissions","phonetic":"/ɪˈmɪʃənz/","definition":"排放物；废气；gases released into the atmosphere","example":"The country pledged to cut carbon emissions by 50% by 2030."},
        {"word":"biodiversity","phonetic":"/ˌbaɪəʊdaɪˈvɜːrsəti/","definition":"生物多样性；the variety of plant and animal life in a habitat","example":"Deforestation threatens biodiversity in the Amazon."},
        {"word":"sustainable","phonetic":"/səˈsteɪnəbəl/","definition":"可持续的；conserving resources for the long term","example":"The company adopted sustainable packaging across all products."},
        {"word":"drought","phonetic":"/draʊt/","definition":"干旱；a prolonged period of abnormally low rainfall","example":"The region experienced its worst drought in 50 years."},
        {"word":"renewable","phonetic":"/rɪˈnjuːəbəl/","definition":"可再生的；energy from sources that are not depleted","example":"Renewable energy now accounts for 40% of the nation's power."},
        {"word":"glacier","phonetic":"/ˈɡlæsiər/","definition":"冰川；a slowly moving mass of ice","example":"Scientists monitor the glacier's retreat as a climate indicator."},
        {"word":"mitigation","phonetic":"/ˌmɪtɪˈɡeɪʃən/","definition":"缓解；减轻；actions to reduce the severity of something","example":"Flood mitigation measures include new drainage systems and levees."},
        {"word":"ecosystem","phonetic":"/ˈiːkəʊsɪstəm/","definition":"生态系统；a biological community of interacting organisms","example":"Coral reef ecosystems are particularly vulnerable to warming oceans."},
        {"word":"resilience","phonetic":"/rɪˈzɪliəns/","definition":"适应力；韧性；the capacity to recover from difficulties","example":"Building climate resilience requires investment in infrastructure."},
        {"word":"conservation","phonetic":"/ˌkɒnsəˈveɪʃən/","definition":"保护；保育；the protection of natural resources","example":"The conservation project restored 10,000 acres of wetlands."},
        {"word":"decarbonization","phonetic":"/diːˌkɑːbənaɪˈzeɪʃən/","definition":"脱碳；去碳化；reducing carbon dioxide emissions from processes","example":"Steelmakers are investing billions in decarbonization technology."},
        {"word":"microplastic","phonetic":"/ˈmaɪkrəʊˌplæstɪk/","definition":"微塑料；tiny plastic particles polluting the environment","example":"Microplastics have been found in human blood samples."},
        {"word":"carbon-neutral","phonetic":"/ˈkɑːrbən ˈnjuːtrəl/","definition":"碳中和的；平衡碳排放；achieving net-zero carbon dioxide emissions","example":"The airline aims to be carbon-neutral by 2040."},
        {"word":"afforestation","phonetic":"/əˌfɒrɪˈsteɪʃən/","definition":"植树造林；planting trees in areas without previous forest cover","example":"Large-scale afforestation could absorb millions of tons of CO2."},
        {"word":"tipping-point","phonetic":"/ˈtɪpɪŋ pɔɪnt/","definition":"临界点；转折点；the critical point where a system changes irreversibly","example":"Scientists warn the Amazon is approaching a tipping point."},
    ],
    "health": [
        {"word":"outbreak","phonetic":"/ˈaʊtbreɪk/","definition":"暴发；疫情；a sudden occurrence of a disease","example":"The outbreak was traced to contaminated water."},
        {"word":"symptom","phonetic":"/ˈsɪmptəm/","definition":"症状；a physical or mental feature indicating a condition","example":"Fever and cough are common symptoms of the illness."},
        {"word":"diagnosis","phonetic":"/ˌdaɪəɡˈnəʊsɪs/","definition":"诊断；identification of the nature of an illness","example":"Early diagnosis dramatically improves treatment outcomes."},
        {"word":"epidemiology","phonetic":"/ˌepɪˌdiːmiˈɒlədʒi/","definition":"流行病学；the study of how diseases spread","example":"Epidemiology data guided the public health response."},
        {"word":"antimicrobial","phonetic":"/ˌæntimaɪˈkrəʊbiəl/","definition":"抗菌的；destroying or inhibiting microorganisms","example":"Antimicrobial resistance is called a silent pandemic."},
        {"word":"placebo","phonetic":"/pləˈsiːbəʊ/","definition":"安慰剂；a substance with no therapeutic effect used in trials","example":"The drug outperformed the placebo in clinical trials."},
        {"word":"geriatric","phonetic":"/ˌdʒeriˈætrɪk/","definition":"老年医学的；relating to the medical care of elderly people","example":"Geriatric wards are under pressure from an ageing population."},
        {"word":"immunization","phonetic":"/ˌɪmjʊnaɪˈzeɪʃən/","definition":"免疫接种；the process of becoming protected against a disease","example":"Childhood immunization rates have recovered to pre-pandemic levels."},
        {"word":"mortality","phonetic":"/mɔːrˈtæləti/","definition":"死亡率；the death rate within a population","example":"Infant mortality has declined sharply over the past decade."},
        {"word":"chronic","phonetic":"/ˈkrɒnɪk/","definition":"慢性的；长期的；persisting for a long time or constantly recurring","example":"Chronic back pain affects millions of office workers."},
        {"word":"oncology","phonetic":"/ɒŋˈkɒlədʒi/","definition":"肿瘤学；the study and treatment of cancer","example":"Advances in oncology have improved survival rates dramatically."},
        {"word":"pandemic","phonetic":"/pænˈdemɪk/","definition":"大流行病；a disease outbreak over a wide geographic area","example":"The pandemic exposed weaknesses in global health systems."},
        {"word":"telemedicine","phonetic":"/ˈtelɪˌmedɪsɪn/","definition":"远程医疗；remote diagnosis and treatment via technology","example":"Telemedicine visits surged during the lockdown."},
        {"word":"antibody","phonetic":"/ˈæntiˌbɒdi/","definition":"抗体；a blood protein that counteracts specific antigens","example":"Antibody tests show whether someone has been previously infected."},
        {"word":"remission","phonetic":"/rɪˈmɪʃən/","definition":"病情缓解；a temporary reduction in the severity of a disease","example":"The patient has been in remission for over two years."},
    ],
    "international": [
        {"word":"annexation","phonetic":"/ˌænekˈseɪʃən/","definition":"吞并；兼并；the act of taking territory by force or without agreement","example":"The annexation was condemned by the UN Security Council."},
        {"word":"blockade","phonetic":"/blɒˈkeɪd/","definition":"封锁；an act of sealing off a place to prevent entry or exit","example":"The naval blockade prevented supplies from reaching the port."},
        {"word":"insurgency","phonetic":"/ɪnˈsɜːrdʒənsi/","definition":"叛乱；起义；an active revolt against an established authority","example":"The insurgency has destabilized the region for over a decade."},
        {"word":"mediation","phonetic":"/ˌmiːdiˈeɪʃən/","definition":"调解；斡旋；intervention to resolve a dispute","example":"UN mediation finally brought both sides to the negotiating table."},
        {"word":"ceasefire","phonetic":"/ˈsiːsfaɪər/","definition":"停火；a temporary suspension of fighting","example":"The ceasefire held for three days before violations were reported."},
        {"word":"defector","phonetic":"/dɪˈfektər/","definition":"叛逃者；a person who abandons their country or cause","example":"The defector provided valuable intelligence about the regime."},
        {"word":"peacekeeping","phonetic":"/ˈpiːskiːpɪŋ/","definition":"维和的；maintaining peace, especially by military forces","example":"Peacekeeping troops were deployed along the disputed border."},
        {"word":"asylum","phonetic":"/əˈsaɪləm/","definition":"庇护；避难；protection granted by a state to foreign refugees","example":"The journalist applied for political asylum after fleeing persecution."},
        {"word":"espionage","phonetic":"/ˈespiənɑːʒ/","definition":"间谍活动；the practice of spying","example":"The diplomat was expelled on charges of industrial espionage."},
        {"word":"extradite","phonetic":"/ˈekstrədaɪt/","definition":"引渡；to hand over a criminal to another jurisdiction","example":"The government agreed to extradite the suspect to face trial."},
        {"word":"coup","phonetic":"/kuː/","definition":"政变；a sudden violent seizure of power","example":"The military coup plunged the country into turmoil."},
        {"word":"proxy-war","phonetic":"/ˈprɒksi wɔːr/","definition":"代理人战争；a war instigated by major powers using third parties","example":"Analysts described the conflict as a proxy war between regional powers."},
        {"word":"embargo","phonetic":"/ɪmˈbɑːrɡəʊ/","definition":"禁运；an official ban on trade with a particular country","example":"The arms embargo was extended for another 12 months."},
        {"word":"humanitarian","phonetic":"/hjuːˌmænɪˈteəriən/","definition":"人道主义的；concerned with promoting human welfare","example":"Humanitarian aid was airlifted to the disaster zone."},
        {"word":"protocol","phonetic":"/ˈprəʊtəkɒl/","definition":"礼仪；外交协议；the official procedure of diplomacy","example":"The meeting was delayed by a dispute over diplomatic protocol."},
    ],
    "business": [
        {"word":"acquisition","phonetic":"/ˌækwɪˈzɪʃən/","definition":"收购；the buying of one company by another","example":"The acquisition valued the startup at $4 billion."},
        {"word":"IPO","phonetic":"/ˌaɪ piː ˈəʊ/","definition":"首次公开募股；Initial Public Offering on a stock exchange","example":"The company's IPO was the largest in tech history."},
        {"word":"stakeholder","phonetic":"/ˈsteɪkˌhəʊldər/","definition":"利益相关者；a person with an interest in a business","example":"The plan must balance the needs of all stakeholders."},
        {"word":"turnover","phonetic":"/ˈtɜːrnəʊvər/","definition":"营业额；员工流失率；total revenue or staff replacement rate","example":"The company reported a turnover of £2.3 billion."},
        {"word":"franchise","phonetic":"/ˈfræntʃaɪz/","definition":"特许经营权；a license to operate a business under an established brand","example":"The fast-food chain operates 5,000 franchise locations worldwide."},
        {"word":"outsourcing","phonetic":"/ˈaʊtˌsɔːrsɪŋ/","definition":"外包；obtaining goods or services from an outside supplier","example":"IT outsourcing reduced costs but raised security concerns."},
        {"word":"benchmark","phonetic":"/ˈbentʃmɑːrk/","definition":"基准；标杆；a standard against which performance is measured","example":"Customer satisfaction scores are the industry benchmark."},
        {"word":"equity","phonetic":"/ˈekwɪti/","definition":"股权；equity；the value of shares in a company","example":"The founders retained a 60% equity stake after the funding round."},
        {"word":"fiscal","phonetic":"/ˈfɪskəl/","definition":"财政的；relating to government revenue and spending","example":"The fiscal year ends on March 31st."},
        {"word":"inventory","phonetic":"/ˈɪnvəntri/","definition":"库存；a complete list of items in stock","example":"The warehouse system tracks inventory in real time."},
        {"word":"leverage","phonetic":"/ˈliːvərɪdʒ/","definition":"杠杆；利用；using borrowed capital or an advantage for gain","example":"The firm used financial leverage to expand rapidly."},
        {"word":"niche","phonetic":"/niːʃ/ or /nɪtʃ/","definition":"小众市场；a specialized segment of the market","example":"The brand found a profitable niche in organic baby food."},
        {"word":"portfolio","phonetic":"/pɔːrtˈfəʊliəʊ/","definition":"投资组合；a range of investments or products","example":"The fund's portfolio includes bonds, stocks, and real estate."},
        {"word":"quarterly","phonetic":"/ˈkwɔːrtərli/","definition":"按季度；每季度的；occurring every three months","example":"Quarterly earnings exceeded analyst expectations."},
        {"word":"windfall","phonetic":"/ˈwɪndfɔːl/","definition":"意外之财；a large unexpected financial gain","example":"The oil discovery brought a windfall to the government."},
    ],
    "energy": [
        {"word":"grid","phonetic":"/ɡrɪd/","definition":"电网；the network of power distribution lines","example":"The aging power grid struggled during the heatwave."},
        {"word":"hydropower","phonetic":"/ˈhaɪdrəʊˌpaʊər/","definition":"水力发电；electricity generated from flowing water","example":"Hydropower provides 60% of the country's electricity."},
        {"word":"offshore","phonetic":"/ˈɒfʃɔːr/","definition":"海上；离岸的；located at sea rather than on land","example":"Offshore wind farms can generate power more consistently."},
        {"word":"refinery","phonetic":"/rɪˈfaɪnəri/","definition":"炼油厂；a facility where crude oil is processed","example":"The refinery processes 500,000 barrels of oil per day."},
        {"word":"fracking","phonetic":"/ˈfrækɪŋ/","definition":"水力压裂；extracting gas by injecting fluid into rock","example":"Fracking has faced strong opposition from environmental groups."},
        {"word":"kilowatt","phonetic":"/ˈkɪləwɒt/","definition":"千瓦；千瓦特；a unit of electrical power","example":"The solar panels generate 5 kilowatts during peak sunlight."},
        {"word":"battery-storage","phonetic":"/ˈbætəri ˈstɔːrɪdʒ/","definition":"电池储能；storing electrical energy for later use","example":"Battery storage solves the intermittency problem of solar power."},
        {"word":"biofuel","phonetic":"/ˈbaɪəʊˌfjuːəl/","definition":"生物燃料；fuel derived from living matter","example":"Airlines are testing biofuels to reduce their carbon footprint."},
        {"word":"geothermal","phonetic":"/ˌdʒiːəʊˈθɜːrməl/","definition":"地热的；relating to heat from the Earth's interior","example":"Iceland gets nearly all its heating from geothermal energy."},
        {"word":"petroleum","phonetic":"/pɪˈtrəʊliəm/","definition":"石油；a liquid mixture used as fuel","example":"The country is a major exporter of petroleum products."},
        {"word":"solar-farm","phonetic":"/ˈsəʊlər fɑːrm/","definition":"太阳能发电场；a large-scale solar power installation","example":"The solar farm covers 2,000 acres in the desert."},
        {"word":"pipeline","phonetic":"/ˈpaɪplaɪn/","definition":"输送管道；a long pipe for transporting oil or gas","example":"The pipeline was temporarily shut down for maintenance."},
        {"word":"fusion","phonetic":"/ˈfjuːʒən/","definition":"核聚变；combining atomic nuclei to release energy","example":"A fusion breakthrough could provide virtually unlimited clean energy."},
        {"word":"spill","phonetic":"/spɪl/","definition":"泄漏；溢出；an accidental release of liquid","example":"The oil spill contaminated 50 miles of coastline."},
        {"word":"surcharge","phonetic":"/ˈsɜːrtʃɑːrdʒ/","definition":"附加费；额外收费；an extra charge added to the basic price","example":"A fuel surcharge was added to all airline tickets."},
    ],
    "society": [
        {"word":"inequality","phonetic":"/ˌɪnɪˈkwɒləti/","definition":"不平等；lack of fairness in the distribution of resources","example":"Income inequality has widened over the past three decades."},
        {"word":"demographics","phonetic":"/ˌdeməˈɡræfɪks/","definition":"人口统计；人口结构；statistical data about population groups","example":"Changing demographics are reshaping the labor market."},
        {"word":"welfare","phonetic":"/ˈwelfeər/","definition":"福利；government support for the disadvantaged","example":"Welfare reforms aim to get more people into work."},
        {"word":"socioeconomic","phonetic":"/ˌsəʊsiəʊˌiːkəˈnɒmɪk/","definition":"社会经济的；relating to the interaction of social and economic factors","example":"Socioeconomic background remains a strong predictor of educational outcomes."},
        {"word":"integration","phonetic":"/ˌɪntɪˈɡreɪʃən/","definition":"融合；整合；the process of combining groups into a unified whole","example":"Integration programs help new arrivals learn the language and customs."},
        {"word":"census","phonetic":"/ˈsensəs/","definition":"人口普查；an official count of a population","example":"The census revealed that the city's population had grown by 15%."},
        {"word":"protest","phonetic":"/ˈprəʊtest/","definition":"抗议；a public demonstration of objection to a policy","example":"Thousands joined the protest against the new labor law."},
        {"word":"marginalized","phonetic":"/ˈmɑːrdʒɪnəlaɪzd/","definition":"被边缘化的；treated as insignificant or peripheral","example":"The program aims to support marginalized communities."},
        {"word":"advocacy","phonetic":"/ˈædvəkəsi/","definition":"倡导；public support for a cause or policy","example":"Patient advocacy groups pushed for faster drug approval."},
        {"word":"grassroots","phonetic":"/ˈɡrɑːsruːts/","definition":"基层的；草根的；originating from ordinary people","example":"The grassroots movement gained momentum on social media."},
        {"word":"constituency","phonetic":"/kənˈstɪtjuənsi/","definition":"选区；选民群体；a body of voters in a specified area","example":"The MP promised to hold regular meetings in her constituency."},
        {"word":"secular","phonetic":"/ˈsekjʊlər/","definition":"世俗的；不受宗教影响的；not connected with religious matters","example":"The country has a secular constitution separating church and state."},
        {"word":"polarized","phonetic":"/ˈpəʊləraɪzd/","definition":"两极分化的；divided into sharply contrasting groups","example":"Public opinion has become increasingly polarized on the issue."},
        {"word":"suburban","phonetic":"/səˈbɜːrbən/","definition":"郊区的；relating to residential areas outside city centers","example":"Suburban home prices rose as families sought more space."},
        {"word":"gentrification","phonetic":"/ˌdʒentrɪfɪˈkeɪʃən/","definition":"士绅化；社区高档化；renovation that displaces lower-income residents","example":"Gentrification has transformed the once-affordable neighborhood."},
    ],
    "science": [
        {"word":"hypothesis","phonetic":"/haɪˈpɒθəsɪs/","definition":"假说；假设；a proposed explanation based on limited evidence","example":"The researchers tested the hypothesis with three experiments."},
        {"word":"breakthrough","phonetic":"/ˈbreɪkθruː/","definition":"突破；重大进展；a sudden important development or discovery","example":"The breakthrough could lead to more efficient solar panels."},
        {"word":"empirical","phonetic":"/ɪmˈpɪrɪkəl/","definition":"基于实验的；经验主义的；based on observation or experiment","example":"The theory lacked empirical evidence until the new study."},
        {"word":"genomics","phonetic":"/dʒɪˈnəʊmɪks/","definition":"基因组学；the study of complete sets of genes","example":"Genomics has transformed our understanding of inherited diseases."},
        {"word":"synthesis","phonetic":"/ˈsɪnθəsɪs/","definition":"合成；综合；the combination of ideas into a coherent whole","example":"Chemical synthesis of the compound took three weeks."},
        {"word":"simulation","phonetic":"/ˌsɪmjʊˈleɪʃən/","definition":"模拟；仿造；the imitation of a real-world process","example":"Climate simulations predict more frequent extreme weather events."},
        {"word":"specimen","phonetic":"/ˈspesɪmɪn/","definition":"标本；样本；an individual sample for scientific examination","example":"The fossil specimen is over 200 million years old."},
        {"word":"nanotechnology","phonetic":"/ˌnænəʊtekˈnɒlədʒi/","definition":"纳米技术；technology at the molecular scale","example":"Nanotechnology is used to deliver drugs directly to cancer cells."},
        {"word":"biometrics","phonetic":"/ˌbaɪəʊˈmetrɪks/","definition":"生物识别；using physical characteristics for identification","example":"Biometrics like fingerprints and iris scans enhance airport security."},
        {"word":"cryogenics","phonetic":"/ˌkraɪəʊˈdʒenɪks/","definition":"低温学；the study of very low temperatures","example":"Cryogenics is essential for preserving biological samples."},
        {"word":"telescope","phonetic":"/ˈtelɪskəʊp/","definition":"望远镜；an instrument to observe distant objects","example":"The space telescope captured images of a galaxy 13 billion light-years away."},
        {"word":"ecosystem","phonetic":"/ˈiːkəʊsɪstəm/","definition":"生态系统；a community of organisms interacting with their environment","example":"The introduction of the species disrupted the entire ecosystem."},
        {"word":"radioactivity","phonetic":"/ˌreɪdiəʊækˈtɪvəti/","definition":"放射性；emission of radiation from atomic nuclei","example":"The site was tested for radioactivity before construction began."},
        {"word":"pathogen","phonetic":"/ˈpæθədʒən/","definition":"病原体；a bacterium or virus that causes disease","example":"The pathogen was identified within 48 hours of the first case."},
        {"word":"crystallography","phonetic":"/ˌkrɪstəˈlɒɡrəfi/","definition":"晶体学；the study of crystal structures","example":"X-ray crystallography revealed the protein's 3D structure."},
    ],
    "education": [
        {"word":"curriculum","phonetic":"/kəˈrɪkjʊləm/","definition":"课程体系；the subjects taught in a school or college","example":"The new curriculum includes mandatory coding classes from age 7."},
        {"word":"literacy","phonetic":"/ˈlɪtərəsi/","definition":"读写能力；素养；the ability to read and write","example":"Digital literacy is now as important as traditional literacy."},
        {"word":"vocational","phonetic":"/vəʊˈkeɪʃənəl/","definition":"职业的；职业培训的；relating to skills for a particular job","example":"Vocational training programs fill gaps in the skilled labor market."},
        {"word":"pedagogy","phonetic":"/ˈpedəɡɒdʒi/","definition":"教学方法；教学法；the method and practice of teaching","example":"Modern pedagogy emphasizes active learning over passive lectures."},
        {"word":"matriculation","phonetic":"/məˌtrɪkjʊˈleɪʃən/","definition":"大学录取；入学；the process of enrolling at a college or university","example":"Matriculation rates have risen for the fifth consecutive year."},
        {"word":"apprenticeship","phonetic":"/əˈprentɪsʃɪp/","definition":"学徒制；a system of training combining work and study","example":"The apprenticeship program offers a path into engineering without a degree."},
        {"word":"accreditation","phonetic":"/əˌkredɪˈteɪʃən/","definition":"认证；官方认可；official recognition that standards are met","example":"The university lost its accreditation over financial irregularities."},
        {"word":"scholarship","phonetic":"/ˈskɒləʃɪp/","definition":"奖学金；a grant for education awarded on merit or need","example":"She won a full scholarship to study at Oxford."},
        {"word":"dissertation","phonetic":"/ˌdɪsərˈteɪʃən/","definition":"博士论文；学位论文；a long essay on a particular subject for a degree","example":"Her dissertation explored the effects of bilingualism on cognitive development."},
        {"word":"remedial","phonetic":"/rɪˈmiːdiəl/","definition":"补习的；弥补性的；intended to improve skills or correct deficiencies","example":"Remedial classes helped students catch up after the disruption."},
        {"word":"tenure","phonetic":"/ˈtenjər/","definition":"终身教职；终身职位；a permanent academic post after probation","example":"She was granted tenure after publishing three influential papers."},
        {"word":"syllabus","phonetic":"/ˈsɪləbəs/","definition":"教学大纲；课程摘要；an outline of a course of study","example":"The syllabus was updated to include more contemporary authors."},
        {"word":"tutorial","phonetic":"/tjuːˈtɔːriəl/","definition":"导师辅导课；辅导；a small group teaching session","example":"The weekly tutorial provides an opportunity for in-depth discussion."},
        {"word":"dormitory","phonetic":"/ˈdɔːrmɪtəri/","definition":"学生宿舍；a building providing accommodation for students","example":"The new dormitory houses 400 students with shared facilities."},
        {"word":"alumnus","phonetic":"/əˈlʌmnəs/","definition":"校友；a former student of a school or college","example":"The alumnus donated $50 million to the university's research fund."},
    ],
    "sports": [
        {"word":"tournament","phonetic":"/ˈtʊərnəmənt/","definition":"锦标赛；联赛；a series of contests for an overall prize","example":"The tournament attracted players from 32 countries."},
        {"word":"underdog","phonetic":"/ˈʌndərdɒɡ/","definition":"劣势方；不被看好的竞争者；a competitor thought to have little chance","example":"The underdog team defied all expectations to reach the final."},
        {"word":"comeback","phonetic":"/ˈkʌmbæk/","definition":"逆转；东山再起；a return to success after a period of difficulty","example":"Her comeback after the injury was one of the year's best stories."},
        {"word":"franchise","phonetic":"/ˈfræntʃaɪz/","definition":"体育特许经营权；体育品牌；a professional sports team as a business","example":"The franchise relocated to a larger city for better revenue."},
        {"word":"endurance","phonetic":"/ɪnˈdjʊərəns/","definition":"耐力；持久力；the ability to keep going for a long time","example":"Marathon running tests both physical and mental endurance."},
        {"word":"rivalry","phonetic":"/ˈraɪvəlri/","definition":"宿敌关系；对抗；competition between long-standing opponents","example":"The rivalry between the two clubs dates back over a century."},
        {"word":"qualifier","phonetic":"/ˈkwɒlɪfaɪər/","definition":"资格赛；预选赛；a preliminary match to enter a competition","example":"The team must win two qualifiers to reach the main tournament."},
        {"word":"season","phonetic":"/ˈsiːzən/","definition":"赛季；体育赛季；a period during which organized sports are played","example":"The season kicks off with the opening match on Saturday."},
        {"word":"coaching","phonetic":"/ˈkəʊtʃɪŋ/","definition":"教练指导；训练；the work of training and directing athletes","example":"Modern coaching relies heavily on data analytics."},
        {"word":"substitution","phonetic":"/ˌsʌbstɪˈtjuːʃən/","definition":"替换；换人；replacing one player with another","example":"A tactical substitution changed the momentum of the game."},
        {"word":"playoff","phonetic":"/ˈpleɪɒf/","definition":"季后赛；附加赛；a match to decide a winner among tied competitors","example":"The team clinched a playoff spot in the final week of the season."},
        {"word":"sprint","phonetic":"/sprɪnt/","definition":"冲刺；短跑；a short race at full speed","example":"She finished the final sprint in under 11 seconds."},
        {"word":"relegation","phonetic":"/ˌrelɪˈɡeɪʃən/","definition":"降级；降入低级别联赛；moving a team to a lower division","example":"The club faces relegation if they lose the next match."},
        {"word":"athletics","phonetic":"/æθˈletɪks/","definition":"田径运动；体育运动；track and field sporting events","example":"The athletics program produced three Olympic medalists this year."},
        {"word":"doping","phonetic":"/ˈdəʊpɪŋ/","definition":"使用兴奋剂；服用禁药；use of banned substances to enhance performance","example":"The athlete received a two-year ban for doping violations."},
    ],
}

# ============================================================
# GRAMMAR BANK — 100+ patterns
# ============================================================
GRAMMAR_BANK = [
    # Conditionals & Hypotheticals
    {"pattern":"First Conditional: If + present, will + base verb","explanation":"Used for real and possible future situations: \"If the vote passes, the law will take effect in January.\"","example":"If the data confirms the trend, the Fed will likely cut rates."},
    {"pattern":"Second Conditional: If + past, would + base verb","explanation":"Used for unlikely or imaginary situations: \"If they had the votes, they would pass the bill.\"","example":"If the country adopted renewable energy now, it would save billions in the long run."},
    {"pattern":"Third Conditional: If + had + past participle, would have + past participle","explanation":"Used for past situations that didn't happen: \"If they had planned ahead, they would have avoided the shortage.\"","example":"If the company had diversified earlier, it would have survived the downturn."},
    {"pattern":"Mixed Conditional: If + past perfect, would + base verb","explanation":"Past condition with present result: \"If the deal had gone through last year, the market would look very different today.\"","example":"If the government had invested in infrastructure, we wouldn't be facing these power outages."},
    {"pattern":"Unless = if not","explanation":"A cleaner alternative: \"unless Congress intervenes\" = \"if Congress does not intervene.\" Common in formal writing.","example":"The merger cannot proceed unless regulators approve it."},

    # Passive Voice
    {"pattern":"Passive Voice: be + past participle","explanation":"Used when the action is more important than who did it: \"The law was passed last night.\" The agent can be omitted or added with 'by'.","example":"The bill was signed into law by the president on Tuesday."},
    {"pattern":"Passive with 'get': get + past participle","explanation":"Informal passive, common in news for negative events: \"got injured,\" \"got caught.\" Adds a sense of the subject being affected.","example":"Three people got trapped in the elevator during the blackout."},
    {"pattern":"Passive Reporting: It is + past participle + that...","explanation":"For attributing claims: \"It is believed that...\" \"It is expected that...\" Distance the writer from the claim.","example":"It is widely believed that the central bank will hold rates steady."},
    {"pattern":"Passive Infinitive: to be + past participle","explanation":"\"The deal is expected to be finalized next week.\" Passive inside an infinitive construction.","example":"The new regulation is scheduled to be implemented by December."},

    # Relative Clauses
    {"pattern":"Defining Relative Clause: who/that/which","explanation":"Identifies which person or thing: \"The law that passed yesterday...\" No commas, essential to meaning.","example":"The candidate who won the primary will face the incumbent in November."},
    {"pattern":"Non-defining Relative Clause: who/which (with commas)","explanation":"Adds extra information: \"The senator, who has served since 2010, announced retirement.\" Commas required.","example":"Tesla, which reported record earnings, saw its stock jump 12 percent."},
    {"pattern":"Reduced Relative Clause: -ing/-ed participle","explanation":"Omit who/that/which + be: \"The bill (which was) passed yesterday\" becomes \"The bill passed yesterday.\" Concise and formal.","example":"The study published in Nature challenges decades of established theory."},
    {"pattern":"Relative Pronoun 'whose'","explanation":"Showing possession: \"The company whose founder stepped down...\" Connects a person/thing to something they own or are associated with.","example":"The startup whose CEO was arrested has filed for bankruptcy."},

    # Modal Verbs
    {"pattern":"Could/Might/May for speculation","explanation":"\"could\" = possibility; \"might\" = weaker possibility; \"may\" = formal possibility. News uses these to avoid stating facts that aren't confirmed.","example":"The negotiations could end as early as next week, sources say."},
    {"pattern":"Must have + past participle (past deduction)","explanation":"Strong inference about the past: \"They must have known about the breach.\" Expresses near-certainty about a past event.","example":"The board must have been aware of the accounting issues before the audit."},
    {"pattern":"Should have + past participle (past regret/expectation)","explanation":"Something was expected but didn't happen: \"The policy should have been reviewed years ago.\" Expresses criticism or unfulfilled expectation.","example":"The safety inspection should have been completed before the launch."},

    # Participles & Gerunds
    {"pattern":"Present Participle as Sentence Opener","explanation":"Starting with -ing phrase adds a simultaneous or causal action: \"Facing mounting pressure, the CEO resigned.\" Makes writing dynamic.","example":"Citing security concerns, the government temporarily suspended the app."},
    {"pattern":"Past Participle as Adjective","explanation":"Using a past participle to describe a state: \"a divided nation,\" \"the exhausted firefighters.\" More vivid than 'very tired.'","example":"The devastated region will take years to rebuild."},
    {"pattern":"Gerund as Subject","explanation":"\"Reducing emissions\" (noun-like verb) as sentence subject: \"Reducing emissions requires international cooperation.\" Formal and academic.","example":"Negotiating a peace deal has proven more difficult than expected."},

    # Tenses & Time
    {"pattern":"Present Perfect: have/has + past participle","explanation":"Links past action to present: \"The company has reduced its workforce by 20%.\" Action in the past with current relevance.","example":"Inflation has cooled significantly since the start of the year."},
    {"pattern":"Past Perfect: had + past participle","explanation":"Action completed before another past action: \"The market had already priced in the news before the official announcement.\"","example":"Rescuers arrived after the building had already collapsed."},
    {"pattern":"Future Perfect: will have + past participle","explanation":"Action completed by a future time: \"By 2030, the project will have cost $50 billion.\"","example":"By next summer, the committee will have reviewed over 100 applications."},
    {"pattern":"'By the time' + clause","explanation":"Used with perfect tenses: \"By the time the meeting ended, the market had already closed.\" Shows a deadline or endpoint for the action.","example":"By the time the first responders arrived, the fire had spread to three buildings."},

    # Reported Speech
    {"pattern":"Reported Speech: backshift of tenses","explanation":"When reporting what someone said, shift tense back: \"will\" → \"would,\" \"is\" → \"was.\" \"She said she was leaving\" (originally 'I am leaving').","example":"The minister said the government was considering all options."},
    {"pattern":"Reporting Verbs: claim, argue, insist, warn, deny","explanation":"Each carries different tone: \"claimed\" (doubt), \"insisted\" (firmness), \"warned\" (danger), \"denied\" (rejection). Choose based on speaker's stance.","example":"Critics argued the policy would disproportionately affect low-income families."},

    # Inversions & Emphasis
    {"pattern":"Inversion after negative adverbials","explanation":"\"Not only did they miss the deadline, but...\" / \"Seldom has a decision caused such controversy.\" Adds dramatic emphasis; formal/ journalist tone.","example":"Not only did the company beat earnings, it also raised its full-year guidance."},
    {"pattern":"Cleft Sentences: It is/was ... that ...","explanation":"\"It was the opposition leader who first raised the issue.\" Emphasizes one part of the sentence by splitting it into two clauses.","example":"It is the lack of enforcement, not the law itself, that critics object to."},
    {"pattern":"Emphatic 'do/does/did'","explanation":"\"The evidence does suggest a pattern.\" Adds emphasis in present/past simple where no auxiliary normally exists.","example":"Despite the controversy, the data does show a clear improvement in outcomes."},

    # Comparisons
    {"pattern":"Double comparatives: the more ..., the more ...","explanation":"\"The longer the conflict drags on, the higher the economic cost.\" Shows proportional increase of two things together.","example":"The more data the system processes, the more accurate its predictions become."},
    {"pattern":"Comparative + and + comparative","explanation":"\"The situation is becoming more and more urgent.\" Indicates gradual ongoing change.","example":"Climate scientists say the evidence is becoming clearer and clearer."},
    {"pattern":"'As ... as' for equality comparisons","explanation":"\"The impact is not as severe as predicted.\" Shows two things are equal (or not). Negative form \"not as ... as\" is extremely common.","example":"The second-quarter results were not as strong as analysts had forecast."},

    # Conjunctions & Transitions
    {"pattern":"'While/Whereas' for contrast","explanation":"Shows contrast between two facts: \"While the economy grew, inequality widened.\" More formal than 'but'; essential for balanced reporting.","example":"While exports rose 8%, domestic consumption fell for the third straight month."},
    {"pattern":"'Given that' / 'In light of' for reasons","explanation":"Introduces a known fact as basis for a conclusion: \"Given that emissions continue to rise, stronger measures are needed.\" Formal and logical.","example":"In light of the new evidence, the court ordered a retrial."},
    {"pattern":"'Despite / In spite of' for concession","explanation":"\"Despite widespread protests, the law was passed.\" Shows surprising outcome that contradicts expectations.","example":"Despite a 15% drop in ad revenue, the company posted a profit."},

    # Noun Phrases & Articles
    {"pattern":"Compound Nouns in News Writing","explanation":"News loves compound nouns: \"cost-of-living crisis,\" \"interest-rate decision.\" Hyphenated compounds pack meaning into a single modifier.","example":"The government announced a multi-billion-dollar infrastructure program."},
    {"pattern":"Articles with Abstract Nouns","explanation":"'The' + abstract noun refers to a specific instance: \"the inflation of the 1970s\" vs zero article for general concepts: \"Inflation erodes savings.\"","example":"The unemployment caused by the factory closure affected 2,000 families."},
    {"pattern":"Noun phrase as headline: omission of 'be'","explanation":"Headlines drop 'be' verbs: \"(The) Prime Minister (is) to Visit Japan.\" 'To + infinitive' replaces future tense in headlines.","example":"Central Bank Expected to Raise Rates Following Inflation Data."},
]

# ============================================================
# SLANG / IDIOM BANK — 60+ expressions
# ============================================================
SLANG_BANK = [
    {"term":"throw in the towel","meaning":"To admit defeat or give up. From boxing when a trainer throws a towel into the ring. \"After months of negotiations, the union threw in the towel.\""},
    {"term":"bite the bullet","meaning":"To face a difficult situation with courage. \"The government finally bit the bullet and raised taxes.\" Often used for tough decisions."},
    {"term":"kick the can down the road","meaning":"To delay a difficult decision instead of dealing with it. \"Lawmakers once again kicked the can down the road on pension reform.\""},
    {"term":"a double-edged sword","meaning":"Something that has both positive and negative effects. \"Social media is a double-edged sword for political campaigns.\""},
    {"term":"the elephant in the room","meaning":"An obvious major problem that everyone is avoiding. \"Climate change was the elephant in the room at the energy summit.\""},
    {"term":"move the goalposts","meaning":"To unfairly change the rules while something is in progress. \"Critics say the regulator keeps moving the goalposts for approval.\""},
    {"term":"a red herring","meaning":"A misleading clue or distraction. \"The tax issue was a red herring; the real problem was mismanagement.\""},
    {"term":"in the driver's seat","meaning":"In control of a situation. \"With the injunction in hand, the union is now firmly in the driver's seat.\""},
    {"term":"raise the bar","meaning":"To set a higher standard or expectation. \"The new emissions targets raise the bar for the entire industry.\""},
    {"term":"a wake-up call","meaning":"An event that alerts people to a problem. \"The bridge collapse was a wake-up call about infrastructure neglect.\""},
    {"term":"a perfect storm","meaning":"A situation where multiple bad things happen at once. \"A perfect storm of drought, wildfire, and heatwave hit the region.\""},
    {"term":"the tip of the iceberg","meaning":"A small visible part of a much larger hidden problem. \"The arrested official is just the tip of the iceberg.\""},
    {"term":"par for the course","meaning":"What is normal or expected in a situation. \"Delays are par for the course in major infrastructure projects.\""},
    {"term":"a game-changer","meaning":"Something that fundamentally changes a situation. \"The new battery technology could be a game-changer for electric vehicles.\""},
    {"term":"drop the ball","meaning":"To fail to do something you were responsible for. \"The agency dropped the ball on the safety inspection.\""},
    {"term":"a flash in the pan","meaning":"Something that initially shows promise but quickly fades. \"Analysts warned the rally might be a flash in the pan.\""},
    {"term":"back to the drawing board","meaning":"Starting over after a failure. \"After the trial verdict, the team went back to the drawing board.\""},
    {"term":"a knee-jerk reaction","meaning":"An automatic, unthinking response. \"The ban was a knee-jerk reaction rather than a considered policy.\""},
    {"term":"a wild card","meaning":"An unpredictable factor. \"The election of an independent candidate introduced a wild card into the parliamentary arithmetic.\""},
    {"term":"steal someone's thunder","meaning":"To take credit or attention from someone. \"The rival announcement threatened to steal the company's product launch thunder.\""},
    {"term":"a blessing in disguise","meaning":"Something that seems bad initially but has a good outcome. \"Being laid off was a blessing in disguise: she started her own company.\""},
    {"term":"go down the drain","meaning":"To be wasted or lost completely. \"Years of diplomatic effort went down the drain after the leaked memo.\""},
    {"term":"put all your eggs in one basket","meaning":"To risk everything on one thing. \"Investors who put all their eggs in one basket lost everything.\""},
    {"term":"jump on the bandwagon","meaning":"To follow a popular trend. \"Companies are jumping on the AI bandwagon without a clear strategy.\""},
    {"term":"a tough nut to crack","meaning":"A difficult problem or person to deal with. \"The North Korean issue remains a tough nut to crack for diplomats.\""},
    {"term":"call the shots","meaning":"To be in charge and make the important decisions. \"In this negotiation, who really calls the shots?\""},
    {"term":"a level playing field","meaning":"A fair situation where everyone has equal chances. \"New regulations aim to create a level playing field for small businesses.\""},
    {"term":"stretch thin","meaning":"Having too few resources to handle demands. \"The emergency services are stretched thin responding to overlapping crises.\""},
    {"term":"the ball is in someone's court","meaning":"It's someone's turn to take action. \"The proposal has been made; now the ball is in the government's court.\""},
    {"term":"see eye to eye","meaning":"To agree completely. \"The two leaders don't see eye to eye on trade policy.\""},
    {"term":"a mountain to climb","meaning":"A very difficult challenge ahead. \"The candidate faces a mountain to climb in the polls.\""},
    {"term":"burn bridges","meaning":"To destroy relationships or options irrevocably. \"The outgoing CEO burned bridges with a scathing exit interview.\""},
    {"term":"cut corners","meaning":"To do something cheaply or quickly at the expense of quality. \"The contractor cut corners on safety, leading to the collapse.\""},
    {"term":"put the cart before the horse","meaning":"To do things in the wrong order. \"Announcing the deal before due diligence is putting the cart before the horse.\""},
    {"term":"stab in the back","meaning":"An act of betrayal by a trusted person. \"A coalition partner's resignation was seen as a stab in the back.\""},
    {"term":"bend over backwards","meaning":"To make extraordinary effort to help or accommodate. \"The government bent over backwards to attract the investment.\""},
    {"term":"a bitter pill to swallow","meaning":"An unpleasant fact that must be accepted. \"The election result was a bitter pill to swallow for the incumbent.\""},
    {"term":"miss the boat","meaning":"To lose an opportunity by being too slow. \"Companies that miss the boat on AI adoption risk obsolescence.\""},
    {"term":"nip it in the bud","meaning":"To stop a problem early before it grows. \"Regulators moved fast to nip the financial contagion in the bud.\""},
    {"term":"rock the boat","meaning":"To cause trouble or disturb a stable situation. \"The director was fired for rocking the boat on diversity issues.\""},
    {"term":"an uphill battle","meaning":"A difficult struggle against strong opposition. \"The reform faces an uphill battle in the upper house.\""},
    {"term":"at the eleventh hour","meaning":"At the last possible moment. \"A deal was struck at the eleventh hour, averting a strike.\""},
    {"term":"sweep under the rug","meaning":"To hide a problem instead of addressing it. \"The scandal was swept under the rug for years.\""},
    {"term":"the writing on the wall","meaning":"Clear signs that something bad is going to happen. \"The layoffs were the writing on the wall for the struggling division.\""},
    {"term":"walk a tightrope","meaning":"To navigate a very delicate situation. \"The prime minister walks a tightrope between competing factions.\""},
    {"term":"turning a blind eye","meaning":"To deliberately ignore something wrong. \"For years, regulators turned a blind eye to the accounting irregularities.\""},
    {"term":"a double standard","meaning":"Applying different rules to different people unfairly. \"Critics pointed out a double standard in how the cases were handled.\""},
    {"term":"read between the lines","meaning":"To understand the hidden meaning. \"Reading between the lines of the Fed statement, economists see a dovish shift.\""},
    {"term":"hit the nail on the head","meaning":"To be exactly right about something. \"The report hit the nail on the head about the root causes.\""},
    {"term":"a house of cards","meaning":"A fragile structure that can easily collapse. \"The fraudulent scheme turned out to be a house of cards.\""},
    {"term":"go the extra mile","meaning":"To make more effort than expected. \"Companies that go the extra mile on customer service gain loyal fans.\""},
    {"term":"hold your ground","meaning":"To refuse to change your position. \"Despite intense lobbying, the minister held her ground on the regulation.\""},
    {"term":"a reality check","meaning":"Something that forces you to face reality. \"The quarterly loss was a reality check for the overconfident startup.\""},
    {"term":"break the ice","meaning":"To ease tension in a social or diplomatic situation. \"A shared joke helped break the ice between the two delegations.\""},
    {"term":"by the book","meaning":"Strictly following rules and procedures. \"The investigation was conducted by the book, leaving no room for appeal.\""},
    {"term":"in the spotlight","meaning":"Receiving intense public attention. \"The company has been in the spotlight since the whistleblower came forward.\""},
    {"term":"crunch time","meaning":"A critical moment when maximum effort is needed. \"It's crunch time for the trade negotiations with the deadline approaching.\""},
    {"term":"a silver lining","meaning":"A positive aspect in an otherwise bad situation. \"The silver lining of the shutdown is that emissions temporarily dropped.\""},
    {"term":"clutch at straws","meaning":"To try desperate measures when nothing else works. \"The defense team was clutching at straws with procedural objections.\""},
    {"term":"lay the groundwork","meaning":"To prepare the foundation for future action. \"The summit laid the groundwork for a broader climate agreement.\""},
]

# ============================================================
# Usage tracker — prevents daily repeats
# ============================================================
def load_tracker():
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"used_vocab": [], "used_grammar": [], "used_slang": [], "last_date": ""}

def save_tracker(tracker):
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f)

def pick_vocab(article_topics, tracker, count=3, exclude=None):
    """Pick vocab words matching the article's topics, avoiding recent repeats.
    exclude: words already used TODAY (same-day hard dedup, never violated)."""
    candidates = []
    for topic in article_topics:
        if topic in VOCAB_BANK:
            for v in VOCAB_BANK[topic]:
                candidates.append((topic, v))

    if not candidates:
        # Fallback: pick from any topic
        for topic, words in VOCAB_BANK.items():
            for v in words:
                candidates.append((topic, v))

    # Filter out recently used (last 90 entries ~ 6 days)
    used_set = set(tracker["used_vocab"][-90:] if tracker["used_vocab"] else [])
    day_excl = set(exclude or ())
    banned = used_set | day_excl
    fresh = [(t, v) for t, v in candidates if v["word"] not in banned]

    # 指定主题的新词不够时，从全部词库类别补齐（词库 180 词，别让 30 词的小池子反复循环）
    if len(fresh) < count:
        picked_words = {v["word"] for _, v in fresh}
        for topic, words in VOCAB_BANK.items():
            for v in words:
                if v["word"] not in banned and v["word"] not in picked_words:
                    fresh.append((topic, v))
                    picked_words.add(v["word"])

    if not fresh:
        # Bank exhausted vs recent history: at minimum enforce same-day dedup
        fresh = [(t, v) for t, v in candidates if v["word"] not in day_excl]

    # Shuffle to avoid always picking from the first matching topic
    random.shuffle(fresh)

    selected = []
    used_topics = set()
    for topic, v in fresh:
        if len(selected) >= count:
            break
        # Prefer different topics for variety
        if topic not in used_topics or len([s for s in selected if s[0] == topic]) < 2:
            selected.append((topic, v))
            used_topics.add(topic)

    # If we don't have enough, fill from fresh without topic constraints
    if len(selected) < count:
        for topic, v in fresh:
            if len(selected) >= count:
                break
            if (topic, v) not in selected:
                selected.append((topic, v))

    return selected

def pick_grammar(tracker):
    """Pick a grammar pattern, avoiding recent repeats."""
    used_set = set(tracker["used_grammar"][-30:] if tracker["used_grammar"] else [])
    fresh = [(i, g) for i, g in enumerate(GRAMMAR_BANK) if g["pattern"][:40] not in used_set]
    if not fresh:
        fresh = [(i, g) for i, g in enumerate(GRAMMAR_BANK)]
    idx, grammar = random.choice(fresh)
    return grammar

def pick_slang(tracker):
    """Pick a slang/idiom, avoiding recent repeats."""
    used_set = set(tracker["used_slang"][-20:] if tracker["used_slang"] else [])
    fresh = [(i, s) for i, s in enumerate(SLANG_BANK) if s["term"] not in used_set]
    if not fresh:
        fresh = [(i, s) for i, s in enumerate(SLANG_BANK)]
    idx, slang = random.choice(fresh)
    return slang

# ============================================================
# EXTRA_DICT — 大词库（从新闻正文提取词汇用）：word -> (音标, 中文, 例句)
# ============================================================
EXTRA_DICT = {
    # ---- 政治/法律/犯罪 ----
    "indictment": ("/ɪnˈdaɪtmənt/", "起诉书；刑事指控", "The grand jury issued an indictment against the executive."),
    "acquittal": ("/əˈkwɪtl/", "无罪释放；宣判无罪", "The trial ended in an acquittal after six weeks."),
    "homicide": ("/ˈhɒmɪsaɪd/", "杀人（案）；他杀", "Police are treating the death as a homicide."),
    "manslaughter": ("/ˈmænslɔːtə/", "过失杀人（较谋杀罪轻）", "He was convicted of manslaughter, not murder."),
    "extortion": ("/ɪkˈstɔːʃn/", "敲诈勒索", "The gang made millions through extortion."),
    "embezzlement": ("/ɪmˈbezlmənt/", "挪用（公款）；侵占", "The manager was jailed for embezzlement of funds."),
    "subpoena": ("/səˈpiːnə/", "传票（法庭命令到庭）", "Congress issued a subpoena for the documents."),
    "injunction": ("/ɪnˈdʒʌŋkʃn/", "禁制令；强制令", "The court granted an injunction halting the strike."),
    "litigation": ("/ˌlɪtɪˈɡeɪʃn/", "诉讼；打官司", "The company faces years of costly litigation."),
    "jurisdiction": ("/ˌdʒʊərɪsˈdɪkʃn/", "司法管辖权；辖区", "The case falls outside the court's jurisdiction."),
    "statute": ("/ˈstætʃuːt/", "成文法；法令", "The statute was passed by parliament last year."),
    "amendment": ("/əˈmendmənt/", "修正案；修改", "The First Amendment protects free speech."),
    "impeachment": ("/ɪmˈpiːtʃmənt/", "弹劾", "The impeachment vote failed in the Senate."),
    "incumbent": ("/ɪnˈkʌmbənt/", "现任者（官员）", "The incumbent mayor is seeking a third term."),
    "constituency": ("/kənˈstɪtjuənsi/", "选区；选民群体", "Rural constituencies swung heavily to the right."),
    "referendum": ("/ˌrefəˈrendəm/", "全民公投", "Voters rejected the proposal in a referendum."),
    "turnout": ("/ˈtɜːnaʊt/", "投票率；出席人数", "Turnout was the highest in thirty years."),
    "landslide": ("/ˈlændslaɪd/", "（选举）压倒性胜利", "She won by a landslide, taking 70% of the vote."),
    "stalemate": ("/ˈsteɪlmeɪt/", "僵局；相持不下", "Talks ended in stalemate over funding."),
    "coalition": ("/ˌkəʊəˈlɪʃn/", "执政联盟；联合政府", "A coalition government was formed after the election."),
    "cabinet": ("/ˈkæbɪnət/", "内阁", "The cabinet met to discuss the crisis."),
    "envoy": ("/ˈenvɔɪ/", "特使；使节", "A special envoy was sent to broker a deal."),
    "extradition": ("/ˌekstrəˈdɪʃn/", "引渡", "The court approved his extradition to the US."),
    "detainee": ("/ˌdiːteɪˈniː/", "被拘留者", "The detainees were held without charge for months."),
    "embargo": ("/ɪmˈbɑːɡəʊ/", "禁运", "The embargo on oil exports was lifted."),
    "tariff": ("/ˈtærɪf/", "关税", "New tariffs raised the price of imported steel."),
    "levy": ("/ˈlevi/", "征收；征税费", "The state levied a new tax on sugary drinks."),
    "deficit": ("/ˈdefɪsɪt/", "赤字；不足", "The budget deficit widened to record levels."),
    "surplus": ("/ˈsɜːpləs/", "盈余；过剩", "The country ran a trade surplus last year."),
    "shutdown": ("/ˈʃʌtdaʊn/", "（政府）停摆；关闭", "The government shutdown entered its third week."),
    "filibuster": ("/ˈfɪlɪbʌstə/", "（议会）阻挠议事", "Senators launched a filibuster to delay the vote."),
    "mandate": ("/ˈmændeɪt/", "授权；选民赋予的执政授权", "The election gave the party a clear mandate for reform."),
    "ballot": ("/ˈbælət/", "选票；投票", "Voters cast their ballots in record numbers."),
    "decree": ("/dɪˈkriː/", "法令；政令", "The president ruled by decree after dissolving parliament."),
    "curfew": ("/ˈkɜːfjuː/", "宵禁", "A night-time curfew was imposed on the capital."),
    "amnesty": ("/ˈæmnəsti/", "大赦；特赦", "The government offered amnesty to those who surrendered."),
    "forensic": ("/fəˈrenzɪk/", "法医的；鉴证的", "Forensic teams examined the scene overnight."),
    "retrial": ("/ˌriːˈtraɪəl/", "再审；重审", "The court ordered a retrial amid new evidence."),
    "plea": ("/pliː/", "（法庭）抗辩；恳求", "He entered a plea of not guilty."),
    "asylum": ("/əˈsaɪləm/", "庇护（权）", "Thousands sought asylum after crossing the border."),
    # ---- 经济/商业 ----
    "benchmark": ("/ˈbentʃmɑːk/", "基准；标杆", "The index is the benchmark for global oil prices."),
    "yield": ("/jiːld/", "收益率；产出", "Bond yields rose sharply after the announcement."),
    "equity": ("/ˈekwəti/", "股本；权益", "The firm sold a 20% equity stake to investors."),
    "stake": ("/steɪk/", "股份；利害关系", "The government holds a golden stake in the company."),
    "merger": ("/ˈmɜːdʒə/", "合并", "The merger would create the country's largest bank."),
    "acquisition": ("/ˌækwɪˈzɪʃn/", "收购；并购", "The acquisition was cleared by regulators."),
    "takeover": ("/ˈteɪkəʊvə/", "接管；收购", "A hostile takeover bid was rejected outright."),
    "bankruptcy": ("/ˈbæŋkrʌptsi/", "破产", "The chain filed for bankruptcy protection."),
    "default": ("/dɪˈfɔːlt/", "违约；拖欠", "The country risks default on its foreign debt."),
    "creditor": ("/ˈkredɪtə/", "债权人", "Creditors agreed to restructure the loans."),
    "collateral": ("/kəˈlætərəl/", "抵押品", "The loans were backed by property collateral."),
    "mortgage": ("/ˈmɔːɡɪdʒ/", "按揭；抵押贷款", "Mortgage rates hit their highest level in a decade."),
    "revenue": ("/ˈrevənjuː/", "营收；财政收入", "Annual revenue grew by 12% year on year."),
    "inventory": ("/ˈɪnvəntri/", "库存；存货", "Retailers cut inventories ahead of the holidays."),
    "procurement": ("/prəˈkjuːmənt/", "采购", "The army opened a new procurement tender."),
    "outsourcing": ("/ˈaʊtsɔːsɪŋ/", "外包", "Outsourcing cut costs but cost local jobs."),
    "workforce": ("/ˈwɜːkfɔːs/", "劳动力；员工总数", "The workforce was cut by a fifth."),
    "payroll": ("/ˈpeɪrəʊl/", "工资单；员工薪资总额", "Small firms struggle with rising payroll costs."),
    "walkout": ("/ˈwɔːkaʊt/", "罢工；集体退场", "Workers staged a walkout over pay."),
    "mediation": ("/ˌmiːdiˈeɪʃn/", "调解", "The dispute went to mediation after talks collapsed."),
    "arbitration": ("/ˌɑːbɪˈtreɪʃn/", "仲裁", "Both sides agreed to binding arbitration."),
    "monopoly": ("/məˈnɒpəli/", "垄断", "Regulators accused the firm of building a monopoly."),
    "antitrust": ("/ˌæntiˈtrʌst/", "反垄断的", "The tech giant faces an antitrust lawsuit."),
    "compliance": ("/kəmˈplaɪəns/", "合规；遵从", "The bank paid a fine for compliance failures."),
    "audit": ("/ˈɔːdɪt/", "审计", "An independent audit found no wrongdoing."),
    "fiscal": ("/ˈfɪskl/", "财政的", "Fiscal policy remains tight ahead of the election."),
    "monetary": ("/ˈmʌnɪtri/", "货币的", "The central bank eased monetary policy."),
    "stimulus": ("/ˈstɪmjələs/", "刺激（措施）；刺激方案", "The government announced a fiscal stimulus package."),
    "dovish": ("/ˈdʌvɪʃ/", "鸽派的（倾向宽松）", "Dovish comments lifted bond prices."),
    "hawkish": ("/ˈhɔːkɪʃ/", "鹰派的（倾向紧缩）", "Hawkish remarks sent stocks lower."),
    "selloff": ("/ˈselɔːf/", "抛售；暴跌", "A global selloff wiped billions off markets."),
    "hedge": ("/hedʒ/", "对冲；防范", "Investors hedge against currency risk."),
    "commodity": ("/kəˈmɒdəti/", "大宗商品", "Commodity prices surged on supply fears."),
    "projection": ("/prəˈdʒekʃn/", "预测；推算", "Growth projections were revised downward."),
    "outlook": ("/ˈaʊtlʊk/", "前景；展望", "The bank cut its economic outlook for 2027."),
    "downturn": ("/ˈdaʊntɜːn/", "衰退；下滑", "The sector is bracing for a deep downturn."),
    "headwinds": ("/ˈhedwɪndz/", "逆风；不利因素", "Exporters face strong headwinds abroad."),
    "devaluation": ("/ˌdiːˌvæljuˈeɪʃn/", "（货币）贬值", "Devaluation made imports far more expensive."),
    "redundancies": ("/rɪˈdʌndənsiz/", "裁员（英式）", "The plant announced 300 redundancies."),
    "logistics": ("/ləˈdʒɪstɪks/", "物流", "Logistics delays pushed up shipping costs."),
    # ---- 科技/科学/医疗 ----
    "generative": ("/ˈdʒenərətɪv/", "生成式的（AI）", "Generative AI is reshaping white-collar work."),
    "prototype": ("/ˈprəʊtətaɪp/", "原型；样机", "The company unveiled a working prototype."),
    "patent": ("/ˈpætnt/", "专利", "The startup holds key patents on the technology."),
    "encryption": ("/ɪnˈkrɪpʃn/", "加密", "The app uses end-to-end encryption."),
    "surveillance": ("/səˈveɪləns/", "监控；监视", "The city expanded its surveillance network."),
    "quantum": ("/ˈkwɒntəm/", "量子", "Quantum computers could break current encryption."),
    "satellite": ("/ˈsætəlaɪt/", "卫星", "The satellite was launched into orbit."),
    "spacecraft": ("/ˈspeɪskrɑːft/", "航天器", "The spacecraft sent back its first images."),
    "payload": ("/ˈpeɪləʊd/", "（火箭）有效载荷", "The rocket carried a heavy payload."),
    "autonomous": ("/ɔːˈtɒnəməs/", "自主的；自动驾驶的", "Autonomous trucks began trial runs."),
    "robotics": ("/rəʊˈbɒtɪks/", "机器人技术", "Robotics is transforming factory floors."),
    "biometric": ("/ˌbaɪəˈmetrɪk/", "生物识别的", "Biometric scanners replaced passwords."),
    "placebo": ("/pləˈsiːbəʊ/", "安慰剂", "The drug outperformed the placebo group."),
    "dosage": ("/ˈdəʊsɪdʒ/", "剂量", "Doctors adjusted the dosage for children."),
    "diagnosis": ("/ˌdaɪəɡˈnəʊsɪs/", "诊断", "Early diagnosis greatly improves survival."),
    "epidemic": ("/ˌepɪˈdemɪk/", "流行病", "The epidemic spread through the region."),
    "pandemic": ("/pænˈdemɪk/", "大流行病", "The pandemic upended daily life."),
    "variant": ("/ˈveəriənt/", "变体；变种", "A new variant was detected in the country."),
    "genome": ("/ˈdʒiːnəʊm/", "基因组", "Scientists mapped the entire genome."),
    "dementia": ("/dɪˈmenʃə/", "痴呆症", "Air pollution is linked to dementia risk."),
    "obesity": ("/əʊˈbiːsəti/", "肥胖症", "Obesity rates keep climbing among children."),
    "diabetes": ("/ˌdaɪəˈbiːtiːz/", "糖尿病", "Cases of diabetes doubled in a decade."),
    "cardiac": ("/ˈkɑːdiæk/", "心脏的", "He suffered cardiac arrest at his desk."),
    "respiratory": ("/rəˈspɪrətri/", "呼吸的", "Hospitals reported a surge in respiratory cases."),
    "opioid": ("/ˈəʊpiɔɪd/", "阿片类药物", "The opioid crisis has devastated the town."),
    "overdose": ("/ˈəʊvədəʊs/", "服药过量", "Overdose deaths hit a record high."),
    "trauma": ("/ˈtrɔːmə/", "创伤；外伤", "Survivors received treatment for trauma."),
    "psychiatric": ("/ˌsaɪkiˈætrɪk/", "精神病的；精神科的", "He spent weeks in psychiatric care."),
    "fatality": ("/fəˈtæləti/", "死亡（事故中）", "There were no fatalities in the crash."),
    "therapy": ("/ˈθerəpi/", "治疗；疗法", "The new therapy slowed the disease."),
    # ---- 气候/能源 ----
    "decarbonize": ("/ˌdiːˈkɑːbənaɪz/", "脱碳；去碳化", "The plan aims to decarbonize power by 2035."),
    "turbine": ("/ˈtɜːbaɪn/", "涡轮机", "Each turbine can power a thousand homes."),
    "reactor": ("/riˈæktə/", "核反应堆", "The reactor was shut down for inspection."),
    "uranium": ("/juˈreɪniəm/", "铀", "The plant enriches uranium for fuel."),
    "meltdown": ("/ˈmeltdaʊn/", "（核）熔毁；崩溃", "Engineers prevented a full meltdown."),
    "pipeline": ("/ˈpaɪplaɪn/", "管道；输油管", "The new pipeline will cross three states."),
    "refinery": ("/rɪˈfaɪnəri/", "炼油厂", "The refinery halted output after the fire."),
    "seismic": ("/ˈsaɪzmɪk/", "地震的", "Seismic activity has increased sharply."),
    "magnitude": ("/ˈmæɡnɪtjuːd/", "（地震）震级；大小", "The quake had a magnitude of 6.8."),
    "aftershock": ("/ˈɑːftəʃɒk/", "余震", "A powerful aftershock struck at dawn."),
    "tsunami": ("/tsuːˈnɑːmi/", "海啸", "The quake triggered a small tsunami."),
    "cyclone": ("/ˈsaɪkləʊn/", "气旋；旋风", "The cyclone made landfall overnight."),
    "torrential": ("/təˈrenʃl/", "（雨）倾盆的", "Torrential rain flooded the streets."),
    "glacier": ("/ˈɡlæsiə/", "冰川", "The glacier has shrunk by a third."),
    "biodiversity": ("/ˌbaɪəʊdaɪˈvɜːsəti/", "生物多样性", "The region is a hotspot of biodiversity."),
    "ecosystem": ("/ˈiːkəʊsɪstəm/", "生态系统", "The whole ecosystem is under threat."),
    "deforestation": ("/ˌdiːˌfɒrɪˈsteɪʃn/", "滥伐森林", "Deforestation accelerated last year."),
    "extinction": ("/ɪkˈstɪŋkʃn/", "灭绝", "The species faces extinction in the wild."),
    "conservation": ("/ˌkɒnsəˈveɪʃn/", "保护； conservation", "Conservation groups welcomed the ruling."),
    "poaching": ("/ˈpəʊtʃɪŋ/", "偷猎", "Poaching has halved the elephant population."),
    # ---- 战争/安全 ----
    "offensive": ("/əˈfensɪv/", "攻势；进攻", "The army launched a major offensive."),
    "truce": ("/truːs/", "休战；停战", "Both sides agreed to a temporary truce."),
    "militia": ("/məˈlɪʃə/", "民兵组织", "Militias control much of the countryside."),
    "insurgency": ("/ɪnˈsɜːdʒənsi/", "叛乱；暴动", "The insurgency has spread to the north."),
    "retaliation": ("/rɪˌtæliˈeɪʃn/", "报复", "The strike was in retaliation for the attack."),
    "artillery": ("/ɑːˈtɪləri/", "火炮；炮兵", "Artillery fire echoed across the city."),
    "shelling": ("/ˈʃelɪŋ/", "炮击", "Heavy shelling forced residents to flee."),
    "siege": ("/siːdʒ/", "围困；围攻", "The city endured a months-long siege."),
    "blockade": ("/blɒˈkeɪd/", "封锁", "The port remains under blockade."),
    "enclave": ("/ˈenkleɪv/", "飞地；孤立地区", "Supplies reached the besieged enclave."),
    "frontline": ("/ˈfrʌntlaɪn/", "前线", "Doctors worked close to the frontline."),
    "ambush": ("/ˈæmbʊʃ/", "伏击", "The convoy was hit in an ambush."),
    "hostage": ("/ˈhɒstɪdʒ/", "人质", "Militants released two hostages."),
    "ransom": ("/ˈrænsəm/", "赎金", "The family refused to pay the ransom."),
    "trafficking": ("/ˈtræfɪkɪŋ/", "非法贩运（人口/毒品）", "Police broke up a trafficking ring."),
    "espionage": ("/ˈespiənɑːʒ/", "间谍活动", "He was charged with espionage."),
    "disinformation": ("/ˌdɪsˌɪnfəˈmeɪʃn/", "虚假信息（蓄意）", "The campaign spread disinformation online."),
    "propaganda": ("/ˌprɒpəˈɡændə/", "宣传（贬义）", "State media poured out propaganda."),
    "censorship": ("/ˈsensəʃɪp/", "审查；封锁", "Censorship tightened before the vote."),
    "crackdown": ("/ˈkrækdaʊn/", "镇压；严打", "A crackdown on protesters began at dawn."),
    "warhead": ("/ˈwɔːhed/", "弹头", "The missile can carry a nuclear warhead."),
    "arsenal": ("/ˈɑːsənl/", "武库；武器储备", "Inspectors catalogued the arsenal."),
    "ammunition": ("/ˌæmjuˈnɪʃn/", "弹药", "The fort ran out of ammunition."),
    "convoy": ("/ˈkɒnvɔɪ/", "车队；护航", "Aid convoys finally reached the city."),
    "warship": ("/ˈwɔːʃɪp/", "军舰", "Two warships were sent to the region."),
    "ballistic": ("/bəˈlɪstɪk/", "弹道的", "The test involved a ballistic missile."),
    "veteran": ("/ˈvetərən/", "老兵；资深者", "Veterans marched to the memorial."),
    "genocide": ("/ˈdʒenəsaɪd/", "种族灭绝", "The court ruled it amounted to genocide."),
    "atrocity": ("/əˈtrɒsəti/", "暴行", "Survivors described the atrocities."),
    "massacre": ("/ˈmæsəkə/", "大屠杀", "The massacre left hundreds dead."),
    "persecution": ("/ˌpɜːsɪˈkjuːʃn/", "迫害", "Many fled religious persecution."),
    "famine": ("/ˈfæmɪn/", "饥荒", "War has pushed the region toward famine."),
    "starvation": ("/stɑːˈveɪʃn/", "饥饿；饿死", "Aid groups warned of mass starvation."),
    "humanitarian": ("/hjuːˌmænɪˈteəriən/", "人道主义的", "A humanitarian corridor was opened."),
    "militant": ("/ˈmɪlɪtənt/", "武装分子；激进的", "Militants claimed the bombing."),
    "extremist": ("/ɪkˈstɪŋmɪst/", "极端分子", "Extremists recruited followers online."),
    "perpetrator": ("/ˈpɜːpətreɪtə/", "作恶者；凶手", "Police are hunting the perpetrators."),
    # ---- 高级动词 ----
    "unveil": ("/ˌʌnˈveɪl/", "公布；推出；揭幕", "The company unveiled its new EV platform."),
    "overhaul": ("/ˈəʊvəhɔːl/", "彻底改革；全面检修", "Ministers vowed to overhaul the tax system."),
    "spearhead": ("/ˈspɪəhed/", "牵头；领军", "She will spearhead the reform effort."),
    "undermine": ("/ˌʌndəˈmaɪn/", "削弱；暗中破坏", "The scandal undermined public trust."),
    "escalate": ("/ˈeskəleɪt/", "升级；加剧", "Fears of war escalated overnight."),
    "exacerbate": ("/ɪɡˈzæsəbeɪt/", "使恶化；加重", "Sanctions exacerbated the shortage."),
    "alleviate": ("/əˈliːvieɪt/", "缓解；减轻", "The fund aims to alleviate poverty."),
    "mitigate": ("/ˈmɪtɪɡeɪt/", "减轻；缓和", "New rules mitigate the worst risks."),
    "curb": ("/kɜːb/", "遏制；抑制", "New taxes aim to curb smoking."),
    "quell": ("/kwel/", "平息；镇压", "Police moved to quell the riots."),
    "repeal": ("/rɪˈpiːl/", "废除（法律）", "Parliament voted to repeal the act."),
    "enact": ("/ɪˈnækt/", "制定（法律）；颁布", "Congress enacted the bill into law."),
    "implement": ("/ˈɪmplɪment/", "实施；执行", "The city will implement the plan next year."),
    "authorize": ("/ˈɔːθəraɪz/", "授权；批准", "The board authorized the buyback."),
    "allocate": ("/ˈæləkeɪt/", "分配；拨给", "The budget allocates more funds to schools."),
    "slash": ("/slæʃ/", "大幅削减", "The firm slashed 5,000 jobs."),
    "plummet": ("/ˈplʌmɪt/", "暴跌；骤降", "Shares plummeted 20% in a day."),
    "dwindle": ("/ˈdwɪndl/", "逐渐减少", "Supplies dwindled as the siege wore on."),
    "outpace": ("/ˌaʊtˈpeɪs/", "超过；跑赢", "Demand is outpacing supply."),
    "outweigh": ("/ˌaʊtˈweɪ/", "超过；比…重要", "The benefits outweigh the risks."),
    "underscore": ("/ˌʌndəˈskɔː/", "强调；凸显", "The crisis underscores the need for reform."),
    "reiterate": ("/riˈɪtəreɪt/", "重申", "The bank reiterated its guidance."),
    "refute": ("/rɪˈfjuːt/", "驳斥；反驳", "Officials refuted the report's claims."),
    "condemn": ("/kənˈdem/", "谴责；判刑", "World leaders condemned the attack."),
    "denounce": ("/dɪˈnaʊns/", "公开谴责；告发", "Opponents denounced the decree."),
    "lambast": ("/læmˈbæst/", "痛斥；猛烈批评", "Critics lambasted the proposal as unworkable."),
    "applaud": ("/əˈplɔːd/", "鼓掌；称赞", "Analysts applauded the decisive action."),
    "advocate": ("/ˈædvəkeɪt/", "提倡；主张", "Doctors advocate earlier screening."),
    "pledge": ("/pledʒ/", "承诺；保证", "The CEO pledged to cut emissions."),
    "vow": ("/vaʊ/", "发誓；立誓", "Victims vowed to fight on."),
    "embark": ("/ɪmˈbɑːk/", "着手；开始（on）", "The country embarked on major reforms."),
    "suspend": ("/səˈspend/", "暂停；中止", "Flights were suspended indefinitely."),
    "halt": ("/hɔːlt/", "停止；阻止", "Talks halted over the dispute."),
    "derail": ("/dɪˈreɪl/", "使脱轨；破坏（进程）", "The scandal derailed the negotiations."),
    "expedite": ("/ˈekspədaɪt/", "加快；加速", "Officials promised to expedite the visas."),
    "streamline": ("/ˈstriːmlaɪn/", "精简；简化", "The law streamlines permitting."),
    "bolster": ("/ˈbəʊlstə/", "加强；支撑", "The aid aims to bolster the economy."),
    "facilitate": ("/fəˈsɪlɪteɪt/", "促进；使便利", "The deal facilitates cross-border trade."),
    "hamper": ("/ˈhæmpə/", "妨碍；阻碍", "Fog hampered rescue efforts."),
    "impede": ("/ɪmˈpiːd/", "阻碍；妨碍", "Bureaucracy impeded the relief effort."),
    "obstruct": ("/əbˈstrʌkt/", "阻挠；妨碍", "He was charged with obstructing justice."),
    "deter": ("/dɪˈtɜː/", "威慑；阻止", "High fines deter speeders."),
    "intimidate": ("/ɪnˈtɪmɪdeɪt/", "恐吓；威胁", "Voters said they were intimidated at polling stations."),
    "prosecute": ("/ˈprɒsɪkjuːt/", "起诉；检控", "The state will prosecute the firm."),
    "indict": ("/ɪnˈdaɪt/", "起诉；指控", "The grand jury indicted him on fraud charges."),
    "acquit": ("/əˈkwɪt/", "宣判无罪", "The jury acquitted her on all counts."),
    "imprison": ("/ɪmˈprɪzn/", "监禁；关押", "He was imprisoned for twelve years."),
    "parole": ("/pəˈrəʊl/", "假释", "She was denied parole again."),
    "extradite": ("/ˈekstrədaɪt/", "引渡", "The court agreed to extradite him."),
    "surrender": ("/səˈrendə/", "投降；自首", "The suspect surrendered to police."),
    "confess": ("/kənˈfes/", "供认；坦白", "He confessed to the killing in court."),
    "allege": ("/əˈledʒ/", "（无确证地）指控", "Prosecutors allege a decade of fraud."),
    "fabricate": ("/ˈfæbrɪkeɪt/", "捏造；伪造", "The report was fabricated, officials said."),
    "falsify": ("/ˈfɔːlsɪfaɪ/", "篡改；伪造", "He falsified the safety records."),
    "disclose": ("/dɪsˈkləʊz/", "披露；公开", "The firm disclosed the breach late."),
    "redact": ("/rɪˈdækt/", "涂黑；删改（敏感内容）", "Names were redacted from the report."),
    "verify": ("/ˈverɪfaɪ/", "核实；验证", "Independent experts verified the footage."),
    "debunk": ("/ˌdiːˈbʌŋk/", "揭穿；证伪", "Fact-checkers debunked the video."),
    "scrutinize": ("/ˈskruːtənaɪz/", "仔细审查", "Regulators scrutinized the deal."),
    "assess": ("/əˈses/", "评估；评定", "Experts assessed the damage as severe."),
    "evaluate": ("/ɪˈvæljueɪt/", "评价；评估", "The panel evaluated 40 bids."),
    "gauge": ("/ɡeɪdʒ/", "估计；测量", "Officials gauge public anger at record highs."),
    # ---- 高级形容词/副词 ----
    "pivotal": ("/ˈpɪvətl/", "关键的；举足轻重的", "The vote marks a pivotal moment."),
    "decisive": ("/dɪˈsaɪsɪv/", "决定性的；果断的", "A decisive victory reshaped the map."),
    "resounding": ("/rɪˈzaʊndɪŋ/", "压倒性的；响亮的", "The plan won resounding approval."),
    "sweeping": ("/ˈswiːpɪŋ/", "全面的；大范围的", "Sweeping reforms hit the sector."),
    "landmark": ("/ˈlændmɑːk/", "里程碑式的", "The landmark ruling set a precedent."),
    "groundbreaking": ("/ˈɡraʊndbreɪkɪŋ/", "开创性的", "The study is groundbreaking."),
    "staggering": ("/ˈstæɡərɪŋ/", "惊人的；难以置信的", "The sums involved are staggering."),
    "alarming": ("/əˈlɑːmɪŋ/", "令人担忧的", "Alarming rates of fraud were reported."),
    "dire": ("/ˈdaɪə/", "极糟的；严峻的", "Patients face dire shortages."),
    "bleak": ("/bliːk/", "黯淡的；荒凉的", "The economic outlook remains bleak."),
    "grim": ("/ɡrɪm/", "严峻的；冷酷的", "Rescuers reported a grim toll."),
    "stark": ("/stɑːk/", "鲜明的；严酷的", "The contrast is stark."),
    "profound": ("/prəˈfaʊnd/", "深刻的；深远的", "The war had a profound impact."),
    "far-reaching": ("/ˌfɑːˈriːtʃɪŋ/", "深远的", "The deal has far-reaching consequences."),
    "widespread": ("/ˈwaɪdspred/", "广泛的；普遍的", "The outage caused widespread disruption."),
    "rampant": ("/ˈræmpənt/", "猖獗的；泛滥的", "Corruption remains rampant."),
    "pervasive": ("/pəˈveɪsɪv/", "无处不在的", "Cheap phones made the app pervasive."),
    "ubiquitous": ("/juːˈbɪkwɪtəs/", " ubiquitous；无处不在的", "Screens are now ubiquitous."),
    "scarce": ("/skeəs/", "稀缺的；不足的", "Fuel is scarce in the enclave."),
    "abundant": ("/əˈbʌndənt/", "充裕的；丰富的", "Rain was abundant this season."),
    "meticulous": ("/məˈtɪkjələs/", "一丝不苟的", "He kept meticulous records."),
    "rigorous": ("/ˈrɪɡərəs/", "严格的；严密的", "The trial followed rigorous protocols."),
    "stringent": ("/ˈstrɪndʒənt/", "严厉的；（标准）严格的", "Stringent rules govern exports."),
    "robust": ("/rəʊˈbʌst/", "强劲的；稳固的", "The economy proved robust."),
    "resilient": ("/rɪˈzɪliənt/", "有韧性的", "Local firms proved resilient."),
    "fragile": ("/ˈfrædʒaɪl/", "脆弱的；易碎的", "The ceasefire remains fragile."),
    "volatile": ("/ˈvɒlətaɪl/", "动荡的；易变的", "Markets stayed volatile all week."),
    "turbulent": ("/ˈtɜːbjələnt/", "动荡的；混乱的", "The country's turbulent decade ended."),
    "chaotic": ("/keɪˈɒtɪk/", "混乱的", "The evacuation was chaotic."),
    "obsolete": ("/ˈɒbsəliːt/", "过时的；废弃的", "The rules are obsolete, judges said."),
    "cutting-edge": ("/ˌkʌtɪŋ ˈedʒ/", "尖端的；最前沿的", "The lab uses cutting-edge equipment."),
    "novel": ("/ˈnɒvl/", "新颖的； novel 小说", "The court faced a novel legal question."),
    "mainstream": ("/ˈmeɪnstriːm/", "主流的", "EVs have gone mainstream."),
    "polarized": ("/ˈpəʊləraɪzd/", "两极分化的", "The country is deeply polarized."),
    "divisive": ("/dɪˈvaɪsɪv/", "引起分歧的", "The issue proved hugely divisive."),
    "contentious": ("/kənˈtenʃəs/", "有争议的", "The clause is the most contentious part."),
    "embattled": ("/ɪmˈbætld/", "陷入困境的", "The embattled CEO finally resigned."),
    "defiant": ("/dɪˈfaɪənt/", "挑衅的；不服从的", "A defiant crowd faced the police line."),
    "adamant": ("/ˈædəmənt/", "坚决的；固执的", "She is adamant that the deal will close."),
    "vehement": ("/ˈviːəmənt/", "激烈的；强烈的", "Vehement protests greeted the plan."),
    "fierce": ("/fɪəs/", "激烈的；猛烈的", "Competition for the contract was fierce."),
    "outright": ("/ˈaʊtraɪt/", "完全的；直截了当的", "The bid was rejected outright."),
    "alleged": ("/əˈledʒd/", "涉嫌的；所谓的", "The alleged fraud spanned five years."),
    "seemingly": ("/ˈsiːmɪŋli/", "表面上；看似", "The seemingly small change proved crucial."),
    "ostensibly": ("/ɒˈstensəbli/", "表面上（说）", "Ostensibly, the trip was about trade."),
    "arguably": ("/ˈɑːɡjuəbli/", "可以说；恐怕", "This is arguably his best film."),
    "notably": ("/ˈnəʊtəbli/", "尤其；显著地", "Prices fell, notably in the capital."),
    "remarkably": ("/rɪˈmɑːkəbli/", "显著地；非凡地", "The city recovered remarkably fast."),
    "increasingly": ("/ɪnˈkriːsɪŋli/", "日益；越来越多地", "Voters are increasingly sceptical."),
    "overwhelmingly": ("/ˌəʊvəˈwelmɪŋli/", "压倒性地", "The union voted overwhelmingly to strike."),
    "reportedly": ("/rɪˈpɔːtɪdli/", "据报道", "The deal is reportedly worth $2bn."),
    # ---- 高级名词 ----
    "turmoil": ("/ˈtɜːmɔɪl/", "动荡；混乱", "The country was in political turmoil."),
    "upheaval": ("/ʌpˈhiːvl/", "剧变；动荡", "The reforms brought years of upheaval."),
    "outcry": ("/ˈaʊtkraɪ/", "强烈抗议；哗然", "The decision sparked a public outcry."),
    "backlash": ("/ˈbæklæʃ/", "强烈反弹；反噬", "The policy faced a fierce backlash."),
    "momentum": ("/məˈmentəm/", "势头；动力", "The campaign is gaining momentum."),
    "impetus": ("/ˈɪmpɪtəs/", "推动力；刺激", "The deal gave new impetus to talks."),
    "catalyst": ("/ˈkætəlɪst/", "催化剂；诱因", "The fire was the catalyst for the strike."),
    "impediment": ("/ɪmˈpedɪmənt/", "障碍；阻碍", "Bureaucracy is the main impediment."),
    "obstacle": ("/ˈɒbstəkl/", "障碍", "Funding remains the biggest obstacle."),
    "dilemma": ("/dɪˈlemə/", "困境；两难", "Ministers face an awkward dilemma."),
    "paradox": ("/ˈpærədɒks/", "悖论；矛盾", "The prosperity paradox puzzles economists."),
    "discrepancy": ("/dɪˈskrepənsi/", "差异；不符", "Auditors found major discrepancies."),
    "uncertainty": ("/ʌnˈsɜːtnti/", "不确定性", "Political uncertainty is hurting investment."),
    "skepticism": ("/ˈskeptɪsɪzəm/", "怀疑；怀疑论", "Experts voiced deep skepticism."),
    "vigil": ("/ˈvɪdʒɪl/", "烛光守夜； vigil 守灵", "Hundreds held a candlelit vigil."),
    "condolences": ("/kənˈdəʊlənsɪz/", "哀悼；慰问", "The president sent his condolences."),
    "tribute": ("/ˈtrɪbjuːt/", "致敬；悼念", "Fans paid tribute to the singer."),
    "autopsy": ("/ˈɔːtɒpsi/", "验尸；尸检", "An autopsy confirmed the cause of death."),
    "inquest": ("/ˈɪŋkwest/", "死因研讯；调查", "The inquest returned a verdict of misadventure."),
    "consensus": ("/kənˈsensəs/", "共识", "Scientists reached a broad consensus."),
    "dissent": ("/dɪˈsent/", "异议；分歧", "The ruling sparked dissent within the party."),
    "solidarity": ("/ˌsɒlɪˈdærəti/", "团结；声援", "Crowds marched in solidarity."),
    "rift": ("/rɪft/", "裂痕；分歧", "The dispute opened a rift between allies."),
    "rivalry": ("/ˈraɪvlri/", "竞争；对抗", "The rivalry dates back decades."),
    "hostility": ("/hɒˈstɪləti/", "敌意；敌对", "Public hostility toward the deal grew."),
    "confrontation": ("/ˌkɒnfrʌnˈteɪʃn/", "对抗；冲突", "The two navies had a brief confrontation."),
    "impasse": ("/ˈɪmpɑːs/", "僵局；死胡同", "Negotiations reached an impasse."),
    "gridlock": ("/ˈɡrɪdlɒk/", "僵局；（交通）瘫痪", "Congressional gridlock delayed the bill."),
    "threshold": ("/ˈθreʃhəʊld/", "门槛；临界点", "The result crossed the legal threshold."),
    "aftermath": ("/ˈɑːftəmæθ/", "后果；余波", "Food prices soared in the aftermath."),
    "legacy": ("/ˈleɡəsi/", "遗产；遗留影响", "Her legacy endures in the party."),
    "precedent": ("/ˈpresɪdənt/", "先例；判例", "The ruling sets a legal precedent."),
    "doctrine": ("/ˈdɒktrɪn/", "学说；主义", "The doctrine guided policy for decades."),
    "ideology": ("/ˌaɪdiˈɒlədʒi/", "意识形态", "The movement fused religion and ideology."),
    "narrative": ("/ˈnærətɪv/", "叙事；说法", "Both sides pushed their own narrative."),
    "discourse": ("/ˈdɪskɔːs/", "话语；论述", "Social media changed public discourse."),
    "agenda": ("/əˈdʒendə/", "议程；意图", "Housing tops the agenda."),
    "manifesto": ("/ˌmænɪˈfestəʊ/", "宣言；政纲", "The party's manifesto pledges reform."),
    "initiative": ("/ɪˈnɪʃətɪv/", "倡议；主动行动", "The peace initiative gained support."),
    "framework": ("/ˈfreɪmwɜːk/", "框架", "A new framework governs the talks."),
    "mechanism": ("/ˈmekənɪzəm/", "机制", "A mechanism for disputes was created."),
    "protocol": ("/ˈprəʊtəkɒl/", "规程；协议", "Staff followed the safety protocol."),
    "provision": ("/prəˈvɪʒn/", "条款；规定", "The provision bans such exports."),
    "regulation": ("/ˌreɡjuˈleɪʃn/", "法规；监管", "New regulation covers AI tools."),
    "milestone": ("/ˈmaɪlstəʊn/", "里程碑", "The launch marks a key milestone."),
    "watershed": ("/ˈwɔːtəʃed/", "分水岭；转折点", "The vote is a watershed moment."),
    "outset": ("/ˈaʊtset/", "开端；起初", "Problems emerged at the outset."),
    "onset": ("/ˈɒnset/", "发作；开始", "The onset of winter worsened conditions."),
    "plight": ("/plaɪt/", "困境；苦境", "The documentary highlighted their plight."),
    "controversy": ("/ˈkɒntrəvɜːsi/", "争议", "The award caused fresh controversy."),
    "ordeal": ("/ɔːˈdiːl/", "磨难；煎熬", "The hostages described their ordeal."),
    "saga": ("/ˈsɑːɡə/", "冗长事件；连续剧式风波", "The takeover saga dragged on for months."),
    "furore": ("/ˈfjʊərɔː/", "轰动；哗然", "The remarks caused a furore."),
    "displacement": ("/dɪsˈpleɪsmənt/", "流离失所；置换", "The war caused mass displacement."),
    "malnutrition": ("/ˌmælnjuˈtrɪʃn/", "营养不良", "Aid groups report rising malnutrition."),
    "shortage": ("/ˈʃɔːtɪdʒ/", "短缺", "A fuel shortage gripped the country."),
    "casualty": ("/ˈkæʒuəlti/", "伤亡人员", "No casualties were reported."),
    "evacuation": ("/ɪˌvækjuˈeɪʃn/", "疏散；撤离", "The evacuation covered 10,000 people."),
    "resilience": ("/rɪˈzɪliəns/", "韧性；复原力", "The city showed remarkable resilience."),
    # ---- 新闻主力词（高频但值得学）----
    "insurance": ("/ɪnˈʃʊərəns/", "保险", "The case fueled anger at insurance firms."),
    "executive": ("/ɪɡˈzekjətɪv/", "高管；主管", "The executive was shot outside his hotel."),
    "debate": ("/dɪˈbeɪt/", "辩论；争论", "The case sparked a national debate."),
    "ban": ("/bæn/", "禁止；禁令", "The Taliban banned women from universities."),
    "deny": ("/dɪˈnaɪ/", "否认；拒绝给予", "Officials denied any involvement."),
    "destroy": ("/dɪˈstrɔɪ/", "摧毁；毁掉", "The strikes destroyed the facility."),
    "spark": ("/spɑːk/", "引发；触发", "The verdict sparked protests nationwide."),
    "resign": ("/rɪˈzaɪn/", "辞职", "The minister resigned over the scandal."),
    "arrest": ("/əˈrest/", "逮捕", "Police arrested two suspects overnight."),
    "shooting": ("/ˈʃuːtɪŋ/", "枪击事件", "The shooting left three people dead."),
    "murder": ("/ˈmɜːdə/", "谋杀", "He faces a murder charge."),
    "victim": ("/ˈvɪktɪm/", "受害者；遇难者", "Victims' families addressed the court."),
    "witness": ("/ˈwɪtnəs/", "证人；目击者", "A key witness changed her testimony."),
    "evidence": ("/ˈevɪdəns/", "证据", "New evidence emerged at trial."),
    "investigation": ("/ɪnˌvestɪˈɡeɪʃn/", "调查", "The investigation lasted 18 months."),
    "trial": ("/ˈtraɪəl/", "审判；试验", "The trial enters its final week."),
    "judge": ("/dʒʌdʒ/", "法官；裁判", "The judge dismissed the charge."),
    "jury": ("/ˈdʒʊəri/", "陪审团", "The jury reached a verdict."),
    "court": ("/kɔːt/", "法院；法庭", "The court upheld the ruling."),
    "guilty": ("/ˈɡɪlti/", "有罪的", "He pleaded guilty to fraud."),
    "verdict": ("/ˈvɜːdɪkt/", "裁决；裁定", "The verdict came after five days."),
    "appeal": ("/əˈpiːl/", "上诉；呼吁", "Lawyers said they would appeal."),
    "release": ("/rɪˈliːs/", "释放；发布", "The hostages were released at dawn."),
    "shoot": ("/ʃuːt/", "枪击；射击", "The guard was shot in the shoulder."),
    "injure": ("/ˈɪndʒə/", "使受伤", "Five passengers were injured."),
    "flee": ("/fliː/", "逃离", "Thousands fled the fighting."),
    "survive": ("/səˈvaɪv/", "幸存；挺过", "No one survived the crash."),
    "relief": ("/rɪˈliːf/", "救济；缓解", "Relief supplies reached the port."),
    "activist": ("/ˈæktɪvɪst/", "活动人士", "Activists demanded his release."),
    "resident": ("/ˈrezɪdənt/", "居民", "Residents described a night of shelling."),
    "civilian": ("/sɪˈvɪliən/", "平民", "Civilian casualties mounted."),
    "launch": ("/lɔːntʃ/", "发起；发射；推出", "The army launched a counterattack."),
    "confirm": ("/kənˈfɜːm/", "证实；确认", "Officials confirmed the death toll."),
    "reject": ("/rɪˈdʒekt/", "拒绝", "The offer was rejected outright."),
    "approve": ("/əˈpruːv/", "批准；赞成", "Regulators approved the drug."),
    "impose": ("/ɪmˈpəʊz/", "施加（制裁/限制）", "The West imposed new sanctions."),
    "boost": ("/buːst/", "促进；提升", "The cut aims to boost growth."),
    "trigger": ("/ˈtrɪɡə/", "引发；触发", "The report triggered a sell-off."),
    "cancel": ("/ˈkænsəl/", "取消", "Flights were cancelled overnight."),
    "postpone": ("/pəˈspəʊn/", "推迟", "The vote was postponed again."),
    "delay": ("/dɪˈleɪ/", "延误；推迟", "Talks were delayed by protests."),
    "deadline": ("/ˈdedlaɪn/", "截止期限", "The deadline expires at midnight."),
    "chip": ("/tʃɪp/", "芯片", "The curbs target advanced chips."),
    "semiconductor": ("/ˌsemikənˈdʌktə/", "半导体", "Semiconductor exports fell sharply."),
    "platform": ("/ˈplætfɔːm/", "平台", "The platform banned the accounts."),
    "breach": ("/briːtʃ/", "（数据）泄露；违反", "The breach exposed millions of records."),
    "hacker": ("/ˈhækə/", "黑客", "Hackers demanded a ransom."),
    "viral": ("/ˈvaɪrəl/", "疯传的", "The clip went viral within hours."),
    "influencer": ("/ˈɪnfluənsə/", "网红；意见领袖", "Influencers promoted the scheme."),
    "emission": ("/ɪˈmɪʃn/", "排放", "Emissions fell for a second year."),
    "carbon": ("/ˈkɑːbən/", "碳", "The tax targets carbon output."),
    "renewable": ("/rɪˈnjuːəbl/", "可再生的", "Renewable capacity doubled."),
    "outbreak": ("/ˈaʊtbreɪk/", "爆发；疫情", "The outbreak was traced to a farm."),
    "disease": ("/dɪˈziːz/", "疾病", "The disease spread along the coast."),
    "infection": ("/ɪnˈfekʃn/", "感染", "Infection rates are falling."),
    "treatment": ("/ˈtriːtmənt/", "治疗；待遇", "Patients waited months for treatment."),
    "healthcare": ("/ˈhelθkeə/", "医疗保健", "Healthcare costs keep rising."),
    "symptom": ("/ˈsɪmptəm/", "症状", "Symptoms appear within days."),
    "unemployment": ("/ˌʌnɪmˈplɔɪmənt/", "失业率", "Unemployment edged up to 5.2%."),
    "layoff": ("/ˈleɪɔːf/", "裁员", "Another round of layoffs began."),
    "growth": ("/ɡrəʊθ/", "增长", "Growth stalled in the third quarter."),
    "decline": ("/dɪˈklaɪn/", "下降；衰退", "Sales declined for a sixth month."),
    "investor": ("/ɪnˈvestə/", "投资者", "Investors welcomed the news."),
    "loan": ("/ləʊn/", "贷款", "The bank wrote off the loan."),
    "budget": ("/ˈbʌdʒɪt/", "预算", "The budget passed by one vote."),
    "funding": ("/ˈfʌndɪŋ/", "拨款；资金", "Federal funding was frozen."),
    "wage": ("/weɪdʒ/", "工资", "Real wages fell for two years."),
    "minister": ("/ˈmɪnɪstə/", "部长；大臣", "The minister defended the policy."),
    "parliament": ("/ˈpɑːləmənt/", "议会", "Parliament reconvened on Monday."),
    "senate": ("/ˈsenət/", "参议院", "The Senate blocked the bill."),
    "congress": ("/ˈkɒŋɡres/", "国会", "Congress faces a shutdown deadline."),
    "election": ("/ɪˈlekʃn/", "选举", "The election is set for June."),
    "vote": ("/vəʊt/", "投票；选票", "Lawmakers voted 220-210."),
    "campaign": ("/kæmˈpeɪn/", "竞选；运动", "Her campaign focused on housing."),
    "policy": ("/ˈpɒləsi/", "政策", "The policy takes effect in May."),
    "official": ("/əˈfɪʃl/", "官员；官方的", "Officials declined to comment."),
    "authorities": ("/ɔːˈθɒrətiz/", "当局", "Authorities urged calm."),
    "spokesperson": ("/ˈspəʊkspɜːsn/", "发言人", "A spokesperson denied the report."),
    "statement": ("/ˈsteɪtmənt/", "声明", "The palace issued a statement."),
    "announce": ("/əˈnaʊns/", "宣布", "The bank announced a rate cut."),
    "warn": ("/wɔːn/", "警告", "Officials warned of shortages."),
    "urge": ("/ɜːdʒ/", "敦促；呼吁", "Ministers urged both sides to talk."),
    "demand": ("/dɪˈmɑːnd/", "要求；需求", "Protesters demanded his resignation."),
    "claim": ("/kleɪm/", "声称；索要", "Militants claimed the attack."),
    "sanction": ("/ˈsæŋkʃn/", "制裁", "Sanctions target the oil sector."),
    "ceasefire": ("/ˈsiːsfaɪə/", "停火", "The ceasefire held overnight."),
    "conflict": ("/ˈkɒnflɪkt/", "冲突", "The conflict entered its third year."),
    "attack": ("/əˈtæk/", "袭击；攻击", "The attack killed 12 soldiers."),
    "strike": ("/straɪk/", "罢工；袭击", "Border staff began a strike."),
    "troops": ("/truːps/", "部队", "Troops withdrew from the city."),
    "military": ("/ˈmɪlətri/", "军队；军事的", "The military denied the strike."),
    "missile": ("/ˈmɪsaɪl/", "导弹", "The missile struck a depot."),
    "drone": ("/drəʊn/", "无人机", "Drone attacks halted flights."),
    "border": ("/ˈbɔːdə/", "边境", "The border crossing stayed shut."),
    "refugee": ("/ˌrefjuˈdʒiː/", "难民", "Refugee camps are overcrowded."),
    "migrant": ("/ˈmaɪɡrənt/", "移民", "Migrants waited at the fence."),
    "crisis": ("/ˈkraɪsɪs/", "危机", "The crisis deepened this week."),
    "protest": ("/ˈprəʊtest/", "抗议", "Protests spread to the capital."),
    "treaty": ("/ˈtriːti/", "条约", "The treaty was signed in 1994."),
    "summit": ("/ˈsʌmɪt/", "峰会；山顶", "Leaders meet at the summit."),
    "negotiation": ("/nɪˌɡəʊʃiˈeɪʃn/", "谈判", "Negotiations resume on Tuesday."),
    "agreement": ("/əˈɡriːmənt/", "协议", "The agreement covers trade."),
    "dispute": ("/dɪˈspjuːt/", "争端；纠纷", "The dispute goes back decades."),
    "tension": ("/ˈtenʃn/", "紧张局势", "Tensions rose along the border."),
    "violence": ("/ˈvaɪələns/", "暴力", "Violence erupted after the vote."),
    "rescue": ("/ˈreskjuː/", "营救；救援", "Rescue teams worked through the night."),
    "evacuate": ("/ɪˈvækjueɪt/", "撤离；疏散", "Villages were evacuated on Tuesday."),
    "emergency": ("/ɪˈmɜːdʒənsi/", "紧急情况", "A state of emergency was declared."),
    "disaster": ("/dɪˈzɑːstə/", "灾难", "The disaster killed hundreds."),
    "flood": ("/flʌd/", "洪水；淹没", "Floods cut off the valley."),
    "wildfire": ("/ˈwaɪldfaɪə/", "野火", "The wildfire tripled in size."),
    "earthquake": ("/ˈɜːθkweɪk/", "地震", "The earthquake struck at dawn."),
    "drought": ("/draʊt/", "干旱", "The drought ruined the harvest."),
    "storm": ("/stɔːm/", "风暴", "The storm battered the coast."),
    "hurricane": ("/ˈhʌrɪkən/", "飓风", "The hurricane made landfall."),
    "heatwave": ("/ˈhiːtweɪv/", "热浪", "The heatwave broke records."),
    "supply": ("/səˈplaɪ/", "供应", "Supply chains remain strained."),
    "desperate": ("/ˈdespərət/", "绝望的；不顾一切的", "Desperate families waited at the gate."),
    "sympathy": ("/ˈsɪmpəθi/", "同情；同情心", "The case drew a wave of sympathy."),
    "stalking": ("/ˈstɔːkɪŋ/", "跟踪骚扰", "He admitted stalking the executive."),
    # ---- 批次3：真实新闻高频缺口词 ----
    "plead": ("/pliːd/", "抗辩；认罪（plead guilty 认罪）", "He will plead guilty next week."),
    "charge": ("/tʃɑːdʒ/", "指控；收费；充电", "He faces six federal charges."),
    "kill": ("/kɪl/", "杀害", "He admitted killing the CEO."),
    "admit": ("/ədˈmɪt/", "承认", "She admitted the mistake."),
    "federal": ("/ˈfedərəl/", "联邦的", "The case moved to federal court."),
    "barrier": ("/ˈbæriə/", "障碍；壁垒", "Language barriers remain a problem."),
    "endanger": ("/ɪnˈdeɪndʒə/", "危及；使处于危险", "The cuts endanger lives."),
    "flogging": ("/ˈflɒɡɪŋ/", "鞭刑；鞭打", "Public floggings were reported."),
    "unrecognisable": ("/ʌnˈrekəɡnaɪzəbl/", "面目全非的；认不出的", "The city is unrecognisable after the war."),
    "carrier": ("/ˈkæriə/", "航空母舰；运输公司", "The carrier left port on Monday."),
    "aircraft carrier": ("/ˈeəkrɑːft ˈkæriə/", "航空母舰", "A second aircraft carrier was deployed."),
    "relieve": ("/rɪˈliːv/", "换防；缓解；接替", "The new carrier will relieve the Lincoln."),
    "aboard": ("/əˈbɔːd/", "在船（飞机）上", "Issues were reported aboard the ship."),
    "navy": ("/ˈneɪvi/", "海军", "The Navy confirmed the deployment."),
    "fuel": ("/ˈfjuːəl/", "加剧；助长（动词）；燃料", "The posts fuelled the crisis."),
    "account": ("/əˈkaʊnt/", "账户；描述（an account of）", "Meta removed dozens of accounts."),
    "advice": ("/ədˈvaɪs/", "建议（名词）", "They sell advice to migrants."),
    "deliver": ("/dɪˈlɪvə/", "运送；交付；发表", "Activists tried to deliver aid."),
    "aid": ("/eɪd/", "援助", "Aid convoys crossed the border."),
    "settler": ("/ˈsetlə/", "定居者；殖民者", "Settlers blocked the road."),
    "occupy": ("/ˈɒkjupaɪ/", "占领；占用", "Troops occupied the hilltop."),
    "besiege": ("/bɪˈsiːdʒ/", "围困；包围", "Their homes were besieged for days."),
    "describe": ("/dɪˈskraɪb/", "描述", "Witnesses described the scene."),
    "rule": ("/ruːl/", "统治（名词/动词）；规则", "Five years under Taliban rule."),
    "crossing": ("/ˈkrɒsɪŋ/", "过境点；横渡", "The crossing closed at dawn."),
    "investigation": ("/ɪnˌvestɪˈɡeɪʃn/", "调查", "A BBC investigation found the accounts."),
    "plead guilty": ("/pliːd ˈɡɪlti/", "认罪（法庭用语）", "He pleaded guilty to all charges."),
}

# ============================================================
# 英文释义补充（详情页第二条：英文 Definition / English gloss）
# 词汇点英文释义来源：VOCAB_BANK 的 definition 已在"；"后内嵌英文；
# 自愈词 / EXTRA_DICT 词无英文则优先查此表，缺失回退为空。
# ============================================================
EN_GLOSS = {
    # 常见新闻词：english gloss（简短、贴近原意）
    "earthquake": "a sudden violent shaking of the ground caused by movement within the earth's crust",
    "rescuers": "people who help save others from danger or disaster",
    "powerful": "having great power, strength, or influence",
    "officials": "people holding public office or authoritative positions",
    "security": "the state of being free from danger or threat; measures taken to ensure safety",
    "crossing": "a place where a road, border, or river can be crossed",
    "migrants": "people who move from one place to another, often in search of work or safety",
    "authorities": "the people or organizations that have official power and responsibility",
    "infrastructure": "the basic physical systems of a country or area, such as roads and power supplies",
    "suggestion": "an idea or plan put forward for consideration",
    "impact": "a strong effect or influence on something or someone",
    "assessment": "an evaluation of the nature, quality, or extent of something",
    "survivors": "people who continue to live after an accident, disaster, or dangerous event",
    "struck": "(past of strike) to hit suddenly and forcefully",
    "killed": "(past of kill) caused to die",
    "hundreds": "a large number, roughly between 200 and 1000",
    "buildings": "structures with walls and roofs, such as houses or offices",
    "response": "a reaction to something; an answer or reply",
    "destruction": "the act of damaging something so badly that it no longer exists",
    "estimate": "an approximate calculation or judgement of a value or amount",
    "measures": "actions taken to achieve a particular purpose",
    "stepped up": "(phrasal) increased or intensified",
    "reports": "accounts or statements describing events or situations",
    "regional": "relating to or characteristic of a region",
    "officers": "members of a police force or a position of authority",
    "overwhelming": "very great in amount; so strong that it is difficult to resist",
    "suspended": "(past of suspend) hung from above; temporarily stopped",
    "operation": "an organized activity or campaign; a medical procedure",
    "effort": "a determined attempt or use of physical/mental energy",
    "additional": "extra; more than the usual or expected number or amount",
    "concern": "a feeling of worry; something that is important to a person",
    "central": "most important; at the centre",
    "confirm": "to state or prove that something is definitely true",
    "derived": "(past of derive) obtained or comes from a source",
}

# 词汇点扩展例句（详情页第二条 example2；缺省回退到词库自带 bank example）
VOCAB_EXAMPLES = {
    "earthquake": "A powerful earthquake hit the coastal region, damaging roads and homes.",
    "rescuers": "Rescuers worked through the night to reach those trapped under the rubble.",
    "powerful": "The powerful storm forced thousands of residents to evacuate.",
    "officials": "Local officials pledged to rebuild the damaged area as quickly as possible.",
    "security": "Extra security was deployed at the border crossing.",
    "crossing": "The border crossing remained open to aid workers throughout the crisis.",
    "migrants": "Many migrants were taken to temporary shelters for food and medical care.",
    "authorities": "The authorities have launched a full investigation into the incident.",
    "infrastructure": "The heavy rains badly damaged the region's infrastructure.",
    "suggestion": "There were suggestions that further talks would be held this week.",
    "impact": "The new policy will have a major impact on small businesses.",
    "assessment": "A rapid assessment of the damage is under way.",
    "survivors": "Survivors described hearing a loud boom just before the collapse.",
    "struck": "The storm struck without warning, catching many residents off guard.",
    "hundreds": "Hundreds of volunteers joined the cleanup operation.",
    "buildings": "Several historic buildings were damaged in the fire.",
    "response": "The government's response to the crisis was widely praised.",
    "destruction": "The scale of destruction left aid workers in shock.",
    "estimate": "Officials estimate that the repairs will cost over a million dollars.",
    "measures": "New security measures will take effect from next month.",
    "stepped up": "Police have stepped up patrols in the area.",
    "reports": "Early reports suggest the fire was accidental.",
    "regional": "The outbreak has now become a regional health emergency.",
    "officers": "Two officers were injured while responding to the call.",
    "overwhelming": "The flood of donations was overwhelming.",
    "suspended": "Flights were suspended until the weather improved.",
    "operation": "A large rescue operation was launched immediately.",
    "effort": "The relief effort involved hundreds of volunteers.",
    "additional": "Additional troops were sent to the border.",
    "concern": "There is growing concern over food shortages.",
    "central": "Safety is central to the whole operation.",
    "confirm": "The health ministry refused to confirm the death toll.",
    "derived": "Much of the city's energy is derived from hydroelectric plants.",
    # —— 新闻常见词的扩展例句（保证第二条例句是完整地道英文）——
    "region": "The storm caused widespread damage across the entire region.",
    "attempt": "The latest attempt to reach a ceasefire collapsed within hours.",
    "dozens": "Dozens of families were left homeless by the overnight flooding.",
    "allow": "The new regulations will allow residents to vote by post.",
    "royal": "The royal couple appeared on the balcony to greet the crowd.",
    "direct": "The cyclone made direct landfall just before dawn.",
    "system": "The warning system failed to alert residents in time.",
    "wind": "Wind speeds reached more than 150 kilometres per hour.",
    "team": "An emergency team was flown in to assess the damage.",
    "social": "Anger spread rapidly across social media after the announcement.",
    "aftershock": "A strong aftershock triggered fresh panic among residents.",
    "torrential": "Torrential downpours caused rivers to burst their banks.",
    "destructive": "The destructive blaze destroyed dozens of homes in minutes.",
    "lethal": "The blast released far more lethal gas than officials admitted.",
    "succession": "The succession law now allows the eldest daughter to inherit the throne.",
    "throne": "The heir is expected to ascend the throne within the year.",
    "migrate": "Many workers migrate to the coast each winter for seasonal jobs.",
    "refugees": "Refugees crossed the border hoping to reach safety.",
    "border": "The border crossing was closed until further notice.",
    "ceasefire": "Both sides pledged to respect the fragile ceasefire.",
    "negotiations": "Negotiations broke down over the question of disarmament.",
    "diplomatic": "The dispute sparked a diplomatic row between the two nations.",
    "embassy": "The embassy issued a warning to its citizens abroad.",
    "sanctions": "New sanctions were imposed on the country's energy exports.",
    "protests": "Protests erupted across several major cities.",
    "demonstrators": "Demonstrators called for an end to the new tax.",
    "deadline": "Negotiators face a midnight deadline to reach a deal.",
    "outbreak": "The outbreak spread quickly through densely populated areas.",
    "vaccine": "The vaccine proved highly effective in clinical trials.",
    "hospital": "Hundreds of patients were rushed to the nearest hospital.",
    "supplies": "Emergency supplies were air-dropped to the stranded villages.",
    "evacuation": "The evacuation was ordered as the storm closed in.",
    "shelter": "Residents were urged to move to higher ground for shelter.",
    "damage": "The full extent of the damage is not yet known.",
    "debris": "Crews worked through the night to clear the debris.",
    "witnesses": "Witnesses reported hearing several loud explosions.",
    "investigation": "A full investigation into the crash is under way.",
    "officials": "Officials said the situation remains under control.",
    "residents": "Residents described a night of terrifying shelling.",
    "casualties": "The number of casualties continues to rise.",
    "fatalities": "Fatalities have been reported in several provinces.",
    "precaution": "As a precaution, all flights were cancelled until dawn.",
    "landslide": "Heavy rain triggered a deadly landslide in the valley.",
    "flooding": "Flooding submerged hundreds of homes along the river.",
    "drought": "The prolonged drought has devastated the harvest.",
    "wildfire": "Thousands of firefighters battled the fast-moving wildfire.",
    "blackout": "A massive blackout left millions without power.",
    "outage": "The power outage lasted for more than two days.",
    "moratorium": "The government announced a temporary moratorium on new drilling.",
    "ratify": "The parliament voted to ratify the landmark treaty.",
    "legislation": "The legislation is expected to pass with a large majority.",
    "inflation": "Inflation has pushed food prices to their highest level in years.",
    "recession": "The country is teetering on the edge of a recession.",
    "unemployment": "Unemployment fell to its lowest rate in a decade.",
    "deficit": "The budget deficit widened beyond initial forecasts.",
    "tariff": "New tariffs were imposed on imported steel.",
    "merger": "The proposed merger between the two banks faces scrutiny.",
    "building": "Several buildings near the coast were badly damaged by the storm.",
    "trap": "Rescuers worked frantically to free workers trapped in the collapsed tunnel.",
    "cross": "Thousands were forced to cross the border in search of safety.",
    "seek": "Thousands of families sought shelter in temporary camps.",
    "soldier": "A soldier was injured during the operation and taken to hospital.",
    "change": "The change of policy came after months of public pressure.",
    "urge": "Leaders urged calm as the tension continued to rise.",
    "search": "Search teams are combing the area for any survivors.",
    "strike": "The first strike hit the city shortly after midnight.",
    "toll": "The death toll from the disaster continues to climb.",
    "rescue": "The rescue operation lasted through the night.",
    "evacuate": "Officials ordered residents to evacuate the danger zone immediately.",
    "reached": "The floodwaters reached record levels in several towns.",
    "accounted": "The causes of the accident have not yet been accounted for fully.",
    "fence": "A new fence was erected along the border to deter crossings.",
    "surge": "A fresh surge of migrants arrived at the border overnight.",
    "detain": "Police detained several suspects for questioning.",
    "authority": "The local authority said the road would reopen by Friday.",
    "assessment": "The agency completed a thorough damage assessment yesterday.",
    "device": "A remote-controlled device was used to disarm the explosive.",
}


# 英文用法/含义补充（俚语点第二条英文释义；从 PHRASAL_EXAMPLES 或搭配提取）
def _lemma_candidates(word):
    """给出 word 的词形还原候选（复数→单数、过去式/进行式→原形等）。"""
    w = word.lower().strip()
    cands = [w]
    if w.endswith("'s") and len(w) > 3:
        cands.append(w[:-2])
    if w.endswith("ies") and len(w) > 4:
        cands.append(w[:-3] + "y")
    if w.endswith("ied") and len(w) > 4:
        cands.append(w[:-3] + "y")
    if w.endswith("ing") and len(w) > 5:
        b = w[:-3]
        if len(b) > 2 and b[-1] == b[-2]:
            b = b[:-1]
        cands.append(b)
        if b.endswith("e"):
            cands.append(b[:-1])
        cands.append(b + "e")
    if w.endswith("ed") and len(w) > 4:
        b = w[:-2]
        cands.append(b)
        if b.endswith("e"):
            cands.append(b[:-1])
        if len(b) > 2 and b[-1] == b[-2]:
            cands.append(b[:-1])
    if w.endswith("s") and len(w) > 3:
        cands.append(w[:-1])
        if w.endswith("es") and len(w) > 4:
            cands.append(w[:-2])
    return cands


def _en_gloss_for(word):
    """返回给定词/词组的简短英文释义；查不到返回 ''。

    查找顺序：ECDICT 全量（en_gloss.py，数千常用词）→ 内嵌手工表 → 词形还原后再查。
    """
    for cand in _lemma_candidates(word):
        hit = _ECDICT_GLOSS.get(cand)
        if hit:
            return hit
        hit2 = EN_GLOSS.get(cand)
        if hit2:
            return hit2
    return ""


# 用于为任一生词生成“第二条扩展例句”的通用新闻句式模板（按词性分组）。
# 用 {w} 嵌入词形，保证 example2 与新闻原句 example 来自不同场景。
_VOCAB_EX2_NOUN = [
    "The report highlighted {w} as a key factor in the decision.",
    "Experts say {w} will remain a central issue in the coming weeks.",
    "The new policy is widely seen as a major step in addressing {w}.",
    "Analysts point to {w} when explaining the market's reaction.",
    "A growing number of people now call attention to {w}.",
    "The debate over {w} is unlikely to end soon.",
    "The incident has once again put {w} under the spotlight.",
    "The latest figures show a clear link between the economy and {w}.",
    "Campaigners welcomed the move, saying it reflects growing concern about {w}.",
]
_VOCAB_EX2_VERB = [
    "Officials urged everyone to {w} the situation carefully.",
    "The company decided to {w} its strategy after the crisis.",
    "Residents were told to {w} the area before nightfall.",
    "The new law will {w} how businesses operate in the region.",
    "Authorities are working to {w} the damage as quickly as possible.",
]
_VOCAB_EX2_ADJ = [
    "The {w} situation has drawn widespread attention.",
    "Experts are concerned about the {w} change in policy.",
    "The report describes the {w} impact on local communities.",
    "Many voters expressed {w} support for the new measure.",
]
# 中文释义词性启发式：以“的/性/化”结尾多为形容词；含动词性标记多为动词；其余按名词。
_VERB_HINTS = ("动词", "使", "进行", "成为", "变得", "搜索", "倾倒", "允许", "穿过", "打击", "袭击")

def _pos_hint(definition_cn):
    d = definition_cn or ""
    if d.endswith("的") or d.endswith("性") or d.endswith("化"):
        return "adj"
    if any(h in d for h in _VERB_HINTS):
        return "verb"
    return "noun"

def _gen_vocab_example2(word, definition_cn=""):
    """为生词生成一条不同于 example1 的扩展例句（不同应用场景，词性匹配）。"""
    w = (word or "").strip()
    if not w:
        return ""
    whole = w.lower()
    pos = _pos_hint(definition_cn)
    pool = {"noun": _VOCAB_EX2_NOUN, "verb": _VOCAB_EX2_VERB, "adj": _VOCAB_EX2_ADJ}[pos]
    key = sum(ord(c) for c in whole) % len(pool)
    return pool[key].replace("{w}", w)


def _example2_for_vocab(word, bank_entry):
    """词汇点 example2：优先专用表（VOCAB_EXAMPLES）；其次用词库自带例句
    （_bank_example，与新闻原句 example1 不同，质量最好）；最后模板生成。
    保证 example2 永远不与 example1 重复。"""
    w = word.lower().strip() if word else ""
    # 1) 专用扩展例句表
    ex2 = VOCAB_EXAMPLES.get(w, "")
    if ex2:
        return ex2
    # 2) 词库原 canned 例句（example1 已被替换为新闻原句，因此必然不同）
    bank_ex = ""
    if bank_entry:
        bank_ex = bank_entry.get("_bank_example") or bank_entry.get("example") or ""
    ex1 = (bank_entry or {}).get("example", "")
    if bank_ex and bank_ex.strip().lower() != ex1.strip().lower():
        return bank_ex
    # 3) 模板生成独立例句（按词性匹配句式）
    defn = (bank_entry or {}).get("definition", "") if bank_entry else ""
    generated = _gen_vocab_example2(word, defn)
    if generated:
        return generated
    # 4) 绝境兜底：仅当 example1 为空时才借用词库自带（否则会造成重复）
    if bank_ex and not ex1:
        return bank_ex
    return ""


def _split_cn_en(definition):
    """把 definition 拆成 (中文, 英文gloss)。若含英文片段（如 '立法；法规；laws made…'），
    以最后一个以拉丁字母开头的 '；' 分节作为英文释义返回。"""
    if not definition:
        return definition, ""
    # 全为中文 → 只有中文
    if not re.search(r"[A-Za-z]{2,}", definition):
        return definition, ""
    # 中文在前、英文在后（用分号/中文句号分隔）
    m = re.search(r"[；;。]((?:[A-Za-z][A-Za-z '’\-]{2,}.*))$", definition)
    if m:
        cn = definition[: m.start(1)].rstrip("；;。 ")
        en = m.group(1).strip()
        return cn, en
    # 无法拆分但含英文：整段当中文（保留原样），英文留空
    return definition, ""


def _en_usage_for_slang(term, meaning, example2):
    """俚语点英文含义（真正的英文释义，而非机翻）：优先分词短语本身 + 英文搭配提示。
    优先级：手工英文释义表 > 从释义括号提取英文搭配 > PHRASAL_EXAMPLES 语境句 > 兜底。
    返回可直接展示在详情页的英文行。"""
    tl = (term or "").strip()
    # 1) 手工英文释义（最准确）
    if tl in SLANG_EN:
        base = SLANG_EN[tl]
        if example2 and example2 not in base:
            return base + ' e.g. "' + example2 + '"'
        return base
    # 2) 从释义括号提取英文搭配（如 meaning 里 '(call for reforms 呼吁改革)'）
    m = re.search(r"[（(]([^）)]*?[A-Za-z][^）)]*?)[）)]", meaning or "")
    if m:
        frag = m.group(1).strip()
        en_m = re.match(r"[A-Za-z][A-Za-z' ,\-]{2,}", frag)
        if en_m and len(en_m.group(0).strip()) > 2:
            col = en_m.group(0).strip()
            return f'"{tl}" — a common English phrase; typical collocation: "{col}".'
    # 3) PHRASAL_EXAMPLES 的英文语境句（当作用法示范）
    pex = PHRASAL_EXAMPLES.get(tl) if "PHRASAL_EXAMPLES" in globals() else None
    if pex:
        return f'Usual usage in everyday/news English — "{pex}"'
    # 4) 兜底英文解释句
    if example2:
        return f'"{tl}" is a common English idiom/phrase in news reporting, usually used like this: "{example2}".'
    return f'"{tl}" is a common phrase in English news reporting.'


# 俚语/习语点的英文释义（比“示例”更接近真实词典释义）
SLANG_EN = {
    "call for": "to demand or request something publicly",
    "carry out": "to perform or complete a task, order, or action",
    "crack down": "to take strong action to stop or punish something",
    "roll out": "to launch or introduce something (a product, plan, service)",
    "kick off": "to begin or start an event or process",
    "weigh in": "to give an opinion or make a comment, often publicly",
    "step down": "to resign from a position or role",
    "ratchet up": "to increase something gradually, step by step",
    "beef up": "to make something stronger, bigger, or more effective",
    "prop up": "to support or keep something (a system, economy) from failing",
    "cash in on": "to profit from or take advantage of a situation",
    "buy time": "to delay events so that you gain more time to prepare",
    "write off": "to accept that a debt or asset is lost; to cancel it",
    "rule out": "to state that something is not possible or not going to happen",
    "roll back": "to reduce or reverse a decision, policy, or increase",
    "clamp down on": "to take strict action to prevent or reduce something",
    "all but": "almost; very nearly",
    "in short supply": "scarce; not enough available to meet demand",
    "in high demand": "much wanted; desired by many people",
    "silver lining": "a positive side to an otherwise bad situation",
    "uphill battle": "a very difficult struggle or challenge",
    "fall short": "to fail to reach a required standard or target",
    "hit back": "to respond forcefully to criticism or an attack",
    "hang in the balance": "to be uncertain; the outcome is not yet decided",
    "behind bars": "in prison; locked up",
    "nothing short of": "nothing less than; completely; entirely",
    "weather the storm": "to survive a difficult period without serious harm",
    "brace for": "to prepare for something difficult or unpleasant that is about to happen",
    "shore up": "to support or strengthen something that is weak or failing",
    "come under fire": "to be strongly criticized",
    "grapple with": "to struggle hard to deal with a difficult problem",
    "grapple": "to struggle hard to deal with a difficult problem",
    "step up": "to increase in amount, speed, or intensity",
    "ramp up": "to increase or raise something, often production or effort",
    "push back against": "to resist or strongly oppose something",
    "push back": "to resist or strongly oppose something",
    "batten down the hatches": "to prepare for a difficult or dangerous situation",
    "bear the brunt": "to suffer the main force or worst part of something",
    "in the wake of": "following something, especially as a consequence",
    "on the ground": "in the place where something is actually happening",
    "on top of": "in addition to; in control of a situation",
    "keep tabs on": "to watch or monitor someone or something closely",
    "zero in on": "to focus attention precisely on something",
    "draw a line": "to set a limit or boundary; to state what is not acceptable",
    "draw the line": "to set a limit or boundary; to state what is not acceptable",
    "lay the groundwork": "to prepare the basis for future work or success",
    "turn the tide": "to change the course of events in someone's favour",
    "tip the scales": "to be the deciding factor; to make one side win",
    "under fire": "being strongly criticized or attacked",
    "on the brink of": "very close to something (often a crisis or change)",
    "at stake": "at risk; something important that could be lost",
    "by and large": "mostly; in general",
    "long haul": "a long and difficult effort over time",
    "a wild card": "an unpredictable factor that could change the outcome",
    "a mountain to climb": "a very large and difficult task ahead",
}


# ============================================================
# PHRASAL_BANK — 新闻短语动词/习语（从新闻正文提取俚语点用）
# ============================================================
PHRASAL_BANK = {
    "call for": "呼吁；要求（call for reforms 呼吁改革）",
    "carry out": "执行；实施（carry out an attack 实施袭击）",
    "crack down": "严厉打击；镇压（crack down on protesters）",
    "roll out": "推出；铺开（roll out a plan 推出计划）",
    "kick off": "开始；启动（kick off a campaign）",
    "weigh in": "发声；介入争论（officials weigh in 官员表态）",
    "step down": "辞职；下台（step down as CEO）",
    "back down": "让步；退缩（refused to back down 拒绝让步）",
    "push for": "力争；敦促（push for a ceasefire）",
    "point to": "指向；表明（evidence points to…）",
    "lead to": "导致（lead to sanctions）",
    "deal with": "处理；应对（deal with the crisis）",
    "hold talks": "举行会谈（hold talks with…）",
    "shore up": "支撑；扶持（shore up the economy）",
    "ramp up": "加码；提速（ramp up production）",
    "lay off": "裁员（lay off workers）",
    "opt for": "选择（opt for a compromise）",
    "forge ahead": "强行推进（forge ahead with reforms）",
    "stand down": "退下；停职（troops stand down）",
    "hit back": "反击；回击（hit back at critics）",
    "pull out": "撤出；退出（pull out of the deal）",
    "walk out": "退场抗议；罢工（delegates walk out）",
    "wipe out": "消灭；抹去（wipe out a village）",
    "draw on": "利用；借鉴（draw on experience）",
    "brace for": "做好准备应对（brace for impact）",
    "grapple with": "费力应对（grapple with inflation）",
    "fend off": "挡开；避开（fend off criticism）",
    "stave off": "暂时避开（stave off bankruptcy）",
    "ride out": "安然度过（ride out the storm）",
    "weather the storm": "熬过难关",
    "in the wake of": "在……之后（随之而来）",
    "on the brink of": "濒临……的边缘",
    "on the verge of": "濒临；快要（on the verge of collapse）",
    "in a bid to": "为了；试图（in a bid to end the war）",
    "in an effort to": "为了；以期",
    "a watershed moment": "分水岭时刻；转折点",
    "a tipping point": "临界点；引爆点",
    "the lion's share": "最大份额",
    "a stark warning": "严厉警告",
    "under fire": "受到猛烈批评（come under fire）",
    "come under fire": "遭到抨击",
    "in the crosshairs": "成为众矢之的",
    "gain traction": "获得关注/势头",
    "take a toll": "造成损害（take a heavy toll）",
    "bear the brunt": "首当其冲",
    "make headway": "取得进展",
    "fall short": "未达标；达不到（fall short of targets）",
    "double down": "加码；执意坚持",
    "walk back": "收回（言论）（walk back the remarks）",
    "press ahead": "继续推进（press ahead with plans）",
    "hang in the balance": "悬而未决；凶吉难卜",
    "up in the air": "悬而未定",
    "on the table": "已摆上台面（可供讨论）",
    "behind bars": "在狱中",
    "face the music": "承担后果；接受惩罚",
    "throw weight behind": "全力支持",
    "cast doubt on": "对……提出质疑",
    "shed light on": "揭示；阐明",
    "keep at bay": "不让……靠近；遏制",
    "iron out": "消除（分歧）（iron out differences）",
    "hash out": "反复磋商出（协议）",
    "whip up": "煽动（情绪）（whip up anger）",
    "fan the flames": "火上浇油；加剧",
    "pass the buck": "推卸责任",
    "take the helm": "掌舵；走马上任",
    "turn the tide": "扭转局面",
    "turn the corner": "渡过难关；出现转机",
    "turn a blind eye": "睁一只眼闭一只眼；视而不见",
    "turn up the heat": "加大压力",
    "ratchet up": "逐步升级；步步收紧",
    "beef up": "加强；充实（beef up security）",
    "prop up": "扶持；支撑（prop up prices）",
    "cash in on": "从……中牟利",
    "buy time": "争取时间",
    "write off": "注销；认定无价值",
    "rule out": "排除；排除可能性",
    "roll back": "回撤；撤销（roll back sanctions）",
    "clamp down on": "取缔；严打",
    "by and large": "总体而言",
    "all but": "几乎；差不多（all but collapsed）",
    "nothing short of": "简直是；无异于",
    "in short supply": "供应不足",
    "in high demand": "需求旺盛",
    "silver lining": "（困境中的）一线希望",
    "uphill battle": "艰苦的斗争",
    "level playing field": "公平竞争环境",
    "the writing is on the wall": "败局已定；迹象明显",
}

# ============================================================
# GRAMMAR_PATTERNS — 语法点：从新闻正文句子中检测（顺序即优先级）
# ============================================================
GRAMMAR_PATTERNS = [
    ("被动语态 (Passive Voice)",
     "be 动词 + 过去分词。新闻大量使用被动语态，因为动作的承受者比执行者更重要。注意 by 短语引出真正的执行者，常被省略。",
     r"\b(?:was|were|is|are|been|being|be)\s+(?:\w+ed|known|held|taken|given|seen|made|found|told|sent|brought|kept|written|driven|caught|built|bought|sold|left|felt|swept|struck|shot|killed|wounded|trapped|forced|ordered|accused|convicted|sentenced|jailed|charged|appointed|elected|injured|displaced|evacuated|deployed|recalled|damaged|destroyed|delayed|suspended|halted|lifted|imposed|approved|rejected|unveiled|released|published|confirmed|announced|reported|launched)\b"),
    ("间接引语 / 转述动词 (Reported Speech)",
     "said/told/warned/confirmed + that 从句（that 常省略）。新闻标题后正文常用转述动词引述当事人观点，注意从句语序不倒装。",
     r"\b(?:said|told|warned|announced|confirmed|added|insisted|explained|noted|stated|claimed|denied|admitted|stressed|argued|urged|pledged|vowed)\b"),
    ("定语从句 (Relative Clause)",
     "who/which/that 引导的定语从句修饰前面的名词。who 指人、which 指物，that 两者皆可；关系代词在从句中作宾语时可省略。",
     r"\b(?:who|which|that|whose|whom)\s+\w+(?:ed|s|ing)?\b"),
    ("现在完成时 (Present Perfect)",
     "have/has + 过去分词。表示过去发生、对现在有影响的动作。新闻中常用来强调\"已经发生\"的结果，常与 already、just、so far 连用。",
     r"\b(?:have|has)\s+(?:\w+ed|grown|known|taken|given|seen|made|found|held|kept|risen|fallen|become|begun|done|gone|come|shown|spoken|written|broken|brought|built|bought|sold|sent|left|felt)\b"),
    ("比较结构 (Comparatives)",
     "more/less/-er + than。用于数字对比，新闻里极常见。注意 than 前后比较对象要对称。",
     r"\b(?:more|less|fewer|higher|lower|bigger|larger|smaller|stronger|weaker|faster|slower|worse|better)\s+\w+\s+than\b"),
    ("条件句 (Conditional)",
     "if 引导的条件从句。真实条件用一般现在时（if X happens, Y will…）；新闻中也常见虚拟条件表假设。",
     r"\b[Ii]f\s+\w+\s+\w+(?:s|ed)?\b"),
    ("将来表达 (Future: will / going to)",
     "will + 动词原形表预测或承诺；be going to 表计划好的事。新闻预测走势、宣布计划时高频出现。",
     r"\b(?:will|going to)\s+\w+\b"),
    ("分词作状语 (Participle Clauses)",
     "现在/过去分词短语(-ing/-ed)放在句首或句末作状语，相当于缩略的从句，使句子更紧凑。如 citing… = while citing…。",
     r"(?:,\s*(?:citing|according to|hailing|urging|warning|saying|calling|adding|speaking|pointing)|^(?:Citing|Hailing|Urging|Warning|Saying|Speaking|Pointing|Following|Battered|Damaged|Hit)\b)"),
    ("as 引导的时间/原因从句",
     "as + 主语 + 谓语：可表\"当…时\"（同时发生）或\"由于\"。比 because 语气弱，新闻叙事常用。",
     r"\bas\s+\w+\s+\w+(?:ed|s)\b"),
    ("动名词作主语 (Gerund Subject)",
     "-ing 形式（动名词）直接作句子主语，谓语用单数。如 Building homes takes time.",
     r"^(?:\w+ing)\s+(?:is|are|has|have|could|can|may|will|remains?|takes?)\b"),
    ("despite / amid + 名词（让步/背景状语）",
     "despite + 名词 = 虽然（= in spite of）；amid + 名词 = 在…的背景之中。注意后面不能接完整从句。",
     r"\b(?:[Dd]espite|[Aa]mid|[Ii]n spite of)\b"),
    ("不定式表目的 (Infinitive of Purpose)",
     "to + 动词原形表目的，相当于 in order to。新闻中 to do 常紧跟动词说明意图。",
     r"\bto\s+(?:end|boost|cut|curb|ease|halt|help|prevent|reduce|support|tackle|address|respond|shore|step|pressure|force|allow|expand|protect|improve)\b"),
    ("最高级 (Superlatives)",
     "the + -est / the most + 形容词。新闻爱用最高级制造冲击力（the largest, the worst since…）。",
     r"\bthe\s+(?:most|least|largest|biggest|highest|lowest|worst|best|strongest|fastest|deadliest)\b"),
    ("新闻标题体 (Headline Grammar)",
     "标题省略冠词与 be 动词、用一般现在时表过去事件（Mangione admits killing… = admitted）。这是新闻英语的标志性语法。",
     r"^(?:[A-Z]\w+){2,}"),
]


def escape_js_string(s):
    if not s:
        return ""
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "")
    return s

# 为 article 的 vocab/grammar/slang 点统一补齐英文释义(en_def/en)与扩展例句(example2)。
# 用于 main()/auto_mode() 等"题库=课文"路径，live 路径已在提取时自带。
def _enrich_article_points(article):
    for v in article.get("vocabPoints", []):
        v.setdefault("example2", _example2_for_vocab(v.get("word", ""), v))
        if not v.get("en_def"):
            _cn, _en = _split_cn_en(v.get("definition", ""))
            if not _en:
                _en = _en_gloss_for(v.get("word", ""))
            if _en:
                if _cn and _cn != v.get("definition", ""):
                    v["definition"] = _cn
                v["en_def"] = _en
    for g in article.get("grammarPoints", []):
        g.setdefault("en", GRAMMAR_EN.get(g.get("pattern", ""), ""))
        g.setdefault("example2", GRAMMAR_GENERIC_EXAMPLES.get(g.get("pattern", ""), ""))
    for s in article.get("slangPoints", []):
        s.setdefault("example", "")
        s.setdefault("example2", _slang_generic_example(s.get("term", ""), s.get("meaning", "")))
        s.setdefault("en", _en_usage_for_slang(s.get("term", ""), s.get("meaning", ""), s.get("example2", "")))

def gen_news_js(article, idx):
    a = article
    _enrich_article_points(a)
    date = a.get("date", "")
    source = a.get("source", "")
    country = a.get("country", "")
    title = a.get("title", "")
    summary = a.get("summary", "")
    body = a.get("body", "")
    url = a.get("url", "")
    news_id = f"n{int(time.time())}_{idx}"

    lines = []
    lines.append("    {")
    lines.append(f"      id: '{news_id}', date: '{escape_js_string(date)}', source: '{escape_js_string(source)}', country: '{escape_js_string(country)}',")
    lines.append(f"      title: '{escape_js_string(title)}',")
    lines.append(f"      summary: '{escape_js_string(summary)}',")
    lines.append(f"      body: '{escape_js_string(body)}',")
    lines.append(f"      url: '{escape_js_string(url)}',")
    lines.append(f"      source_type: '{a.get('source_type', 'template')}',")
    lines.append("      vocabPoints: [")

    for v in a.get("vocabPoints", []):
        lines.append(f"        {{word:'{escape_js_string(v['word'])}',phonetic:\"{escape_js_string(v['phonetic'])}\",definition:'{escape_js_string(v['definition'])}',en_def:'{escape_js_string(v.get('en_def',''))}',example:'{escape_js_string(v['example'])}',example2:'{escape_js_string(v.get('example2',''))}'}},")

    lines.append("      ],")
    lines.append("      grammarPoints: [")

    for g in a.get("grammarPoints", []):
        lines.append(f"        {{pattern:'{escape_js_string(g['pattern'])}',explanation:'{escape_js_string(g['explanation'])}',en:'{escape_js_string(g.get('en',''))}',example:'{escape_js_string(g['example'])}',example2:'{escape_js_string(g.get('example2',''))}'}},")

    lines.append("      ],")
    lines.append("      slangPoints: [")

    for s in a.get("slangPoints", []):
        lines.append(f"        {{term:'{escape_js_string(s['term'])}',meaning:'{escape_js_string(s['meaning'])}',en:'{escape_js_string(s.get('en',''))}',example:'{escape_js_string(s.get('example',''))}',example2:'{escape_js_string(s.get('example2',''))}'}},")

    lines.append("      ]")
    lines.append("    },")
    return "\n".join(lines)

def gen_vocab_js(article, idx):
    lines = []
    date = article.get("date", "")
    date_key = date.replace("-", "")  # e.g. 20260812
    source_short = article.get("source", "") + " - " + article.get("title", "")[:30]
    for i, v in enumerate(article.get("vocabPoints", [])):
        vid = f"v_{date_key}_{idx}_{i}"
        lines.append(
            f"    {{id:'{vid}',word:'{escape_js_string(v['word'])}',phonetic:\"{escape_js_string(v['phonetic'])}\","
            f"definition:'{escape_js_string(v['definition'])}',en_def:'{escape_js_string(v.get('en_def',''))}',"
            f"example:'{escape_js_string(v['example'])}',example2:'{escape_js_string(v.get('example2',''))}',"
            f"source:'{escape_js_string(source_short)}',mastered:false,"
            f"reviewDate:'{escape_js_string(date)}',reviewCount:0,dateAdded:'{escape_js_string(date)}'}},"
        )
    return "\n".join(lines)

def gen_grammar_js(article, idx):
    lines = []
    date = article.get("date", "")
    date_key = date.replace("-", "")  # e.g. 20260812
    source = article.get("source", "")
    for i, g in enumerate(article.get("grammarPoints", [])):
        gid = f"g_{date_key}_{idx}_{i}"
        lines.append(
            f"    {{id:'{gid}',pattern:'{escape_js_string(g['pattern'])}',"
            f"explanation:'{escape_js_string(g['explanation'])}',en:'{escape_js_string(g.get('en',''))}',"
            f"example:'{escape_js_string(g['example'])}',example2:'{escape_js_string(g.get('example2',''))}',"
            f"source:'{escape_js_string(source)}',"
            f"mastered:false,reviewDate:'{escape_js_string(date)}',dateAdded:'{escape_js_string(date)}'}},"
        )
    return "\n".join(lines)

# ============================================================
# Main
# ============================================================
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 update_news.py news_data.json")
        sys.exit(1)

    json_path = sys.argv[1]
    with open(json_path, "r", encoding="utf-8") as f:
        articles = json.load(f)

    if not isinstance(articles, list) or len(articles) == 0:
        print("ERROR: news_data.json must contain a non-empty array")
        sys.exit(1)

    # Load usage tracker
    tracker = load_tracker()

    # Auto-fill vocab, grammar, slang for each article
    for idx, article in enumerate(articles):
        topics = article.get("topics", ["politics", "economy"])
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",")]

        # Pick 3 vocab words from matching topics
        vocab_picks = pick_vocab(topics, tracker, 3)
        article["vocabPoints"] = [v for _, v in vocab_picks]
        for _, v in vocab_picks:
            if v["word"] not in tracker["used_vocab"]:
                tracker["used_vocab"].append(v["word"])

        # Pick 1 grammar
        grammar = pick_grammar(tracker)
        article["grammarPoints"] = [grammar]
        if grammar["pattern"][:40] not in tracker["used_grammar"]:
            tracker["used_grammar"].append(grammar["pattern"][:40])

        # Pick 1 slang
        slang = pick_slang(tracker)
        article["slangPoints"] = [slang]
        if slang["term"] not in tracker["used_slang"]:
            tracker["used_slang"].append(slang["term"])

    # Trim tracker to prevent unlimited growth
    tracker["used_vocab"] = tracker["used_vocab"][-200:]
    tracker["used_grammar"] = tracker["used_grammar"][-100:]
    tracker["used_slang"] = tracker["used_slang"][-60:]
    tracker["last_date"] = articles[0].get("date", "")
    save_tracker(tracker)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Insert news articles
    news_marker = "  return [\n"
    news_idx = html.find(news_marker)
    if news_idx == -1:
        news_marker = "  return ["
        news_idx = html.find(news_marker, html.find("function getDefaultNews"))

    if news_idx == -1:
        print("ERROR: Could not find getDefaultNews return array")
        sys.exit(1)

    insert_pos = news_idx + len(news_marker)
    today = articles[0].get("date", "")
    news_block = f"    // ===== {today} =====\n"
    for idx, article in enumerate(articles):
        news_block += gen_news_js(article, idx) + "\n"

    html = html[:insert_pos] + "\n" + news_block + html[insert_pos:]

    # 2. Insert vocab entries
    vocab_end_marker = "  ];\n}\n\nfunction getDefaultGrammar"
    vocab_end_idx = html.find(vocab_end_marker)
    if vocab_end_idx == -1:
        print("ERROR: Could not find getDefaultVocab end")
        sys.exit(1)

    vocab_block = ""
    for idx, article in enumerate(articles):
        vocab_block += gen_vocab_js(article, idx) + "\n"

    html = html[:vocab_end_idx] + vocab_block + html[vocab_end_idx:]

    # 3. Insert grammar entries
    grammar_end_marker = "  ];\n}\n\nfunction getDefaultSettings"
    grammar_end_idx = html.find(grammar_end_marker)
    if grammar_end_idx == -1:
        print("ERROR: Could not find getDefaultGrammar end")
        sys.exit(1)

    grammar_block = ""
    for idx, article in enumerate(articles):
        grammar_block += gen_grammar_js(article, idx) + "\n"

    html = html[:grammar_end_idx] + grammar_block + html[grammar_end_idx:]

    # Write updated HTML
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    vocab_count = sum(len(a.get("vocabPoints", [])) for a in articles)
    grammar_count = sum(len(a.get("grammarPoints", [])) for a in articles)
    slang_count = sum(len(a.get("slangPoints", [])) for a in articles)
    print(f"SUCCESS: Injected {len(articles)} news + {vocab_count} vocab + {grammar_count} grammar + {slang_count} slang into {HTML_FILE}")

# ============================================================
# NEWS TEMPLATES — 10 sets × 5 articles = 50 templates
# Auto mode picks a set based on day-of-year, cycling every 10 days
# Combined with 500+ vocab bank + usage tracker, content stays fresh
# ============================================================
NEWS_TEMPLATES = [
    # ---- SET 0 ----
    [
        {"source":"BBC","country":"UK","title":"UK Government Unveils Planning Reform to Accelerate Housebuilding","summary":"Ministers announced sweeping changes to planning rules, targeting 1.5 million new homes over five years. Critics warned the reforms could override local objections and damage greenbelt protections.","url":"https://www.bbc.com/news/uk-planning-reform","topics":["politics","economy","society"]},
        {"source":"CNN","country":"US","title":"White House Considers Tighter Controls on AI Chip Exports","summary":"The administration is weighing expanded restrictions on advanced AI chip shipments to more countries. Tech industry leaders warned the move could hand a competitive edge to foreign rivals.","url":"https://www.cnn.com/business/ai-chip-controls","topics":["tech_ai","politics","business"]},
        {"source":"AP News","country":"US","title":"Record Heat Wave Pushes Southwest Power Grids to the Brink","summary":"Temperatures surpassed 120 degrees Fahrenheit in parts of Arizona and Nevada, straining power infrastructure. Officials urged residents to conserve energy as rolling blackouts loomed.","url":"https://apnews.com/heatwave-power-grid","topics":["climate","energy","health"]},
        {"source":"Reuters","country":"UK","title":"Global Markets Rally as Central Banks Signal Pause on Rate Hikes","summary":"Stock markets surged worldwide after the Federal Reserve and Bank of England hinted interest rates may have peaked. Investors bet on a soft landing for the global economy.","url":"https://www.reuters.com/markets/rally-rate-pause","topics":["economy","business","international"]},
        {"source":"The Guardian","country":"UK","title":"Scientists Report Breakthrough in Lab-Grown Heat-Resistant Coral","summary":"Researchers announced they have successfully cultivated heat-resistant coral in laboratory conditions, offering hope for dying reefs worldwide. The technique could restore damaged ecosystems within a decade.","url":"https://www.theguardian.com/science/coral-breakthrough","topics":["science","climate","health"]},
    ],
    # ---- SET 1 ----
    [
        {"source":"BBC","country":"UK","title":"NHS Faces Winter Crisis as Waiting Lists Hit Record High","summary":"Hospital waiting lists in England reached a new record, with over 7.5 million people awaiting treatment. The health secretary pledged additional funding but unions demanded structural reform.","url":"https://www.bbc.com/news/health-nhs-waiting","topics":["health","politics","society"]},
        {"source":"CNN","country":"US","title":"Federal Reserve Holds Rates Steady, Signals Cuts Later This Year","summary":"The central bank kept its benchmark interest rate unchanged for the fifth consecutive meeting. The statement noted progress on inflation but said more evidence was needed before easing policy.","url":"https://www.cnn.com/economy/fed-rates-decision","topics":["economy","business","politics"]},
        {"source":"AP News","country":"US","title":"Wildfires Force Mass Evacuations Across Three Western States","summary":r"Fast-moving wildfires burned through tens of thousands of acres in California, Oregon, and Washington. Firefighters from as far as Australia arrived to help contain the blazes.","url":"https://apnews.com/wildfires-western-states","topics":["climate","energy","international"]},
        {"source":"Reuters","country":"UK","title":"EU Reaches Landmark Deal on AI Regulation Act","summary":"European lawmakers and member states agreed on the final text of sweeping rules governing artificial intelligence. The law bans certain uses of AI and imposes strict transparency requirements on others.","url":"https://www.reuters.com/technology/ai-regulation-deal","topics":["tech_ai","politics","international"]},
        {"source":"The Guardian","country":"UK","title":"New Study Links Air Pollution to Increased Dementia Risk","summary":"Researchers found that people living in areas with high particulate matter concentrations were 40 percent more likely to develop dementia. The findings add pressure on governments to tighten clean air standards.","url":"https://www.theguardian.com/science/air-pollution-dementia","topics":["health","science","climate"]},
    ],
    # ---- SET 2 ----
    [
        {"source":"BBC","country":"UK","title":"UK Inflation Drops to Two-Year Low, Easing Cost of Living Pressure","summary":"Consumer price inflation fell to its lowest level in two years, raising hopes that the worst of the cost-of-living crisis has passed. However, food prices remain stubbornly high for many households.","url":"https://www.bbc.com/news/economy-inflation-drop","topics":["economy","society","politics"]},
        {"source":"CNN","country":"US","title":"Congress Passes Bipartisan Infrastructure Bill After Months of Negotiation","summary":"Lawmakers approved a sweeping infrastructure package worth over one trillion dollars, funding roads, bridges, broadband, and clean energy projects. The bill now heads to the president's desk for signature.","url":"https://www.cnn.com/politics/infrastructure-bill","topics":["politics","economy","energy"]},
        {"source":"AP News","country":"US","title":"Pharmaceutical Giant Announces Breakthrough Alzheimer's Drug","summary":"A major drugmaker reported that its experimental treatment slowed cognitive decline by 35 percent in late-stage trials. Experts called the results a watershed moment, though questions remain about safety and cost.","url":"https://apnews.com/health/alzheimers-drug","topics":["health","science","business"]},
        {"source":"Reuters","country":"UK","title":"UN Climate Summit Ends with Historic Fossil Fuel Transition Pledge","summary":"Nearly 200 nations agreed for the first time to transition away from fossil fuels, in a deal hailed as historic. However, activists criticized the lack of binding timelines and accountability measures.","url":"https://www.reuters.com/world/cop-summit-fossil-fuels","topics":["climate","international","energy"]},
        {"source":"The Guardian","country":"UK","title":"Tech Workers Face Layoffs as Industry Shifts Toward AI Integration","summary":"Major technology companies announced thousands of job cuts, citing a strategic pivot toward artificial intelligence. Employees who built legacy products found their skills suddenly in low demand.","url":"https://www.theguardian.com/technology/tech-layoffs-ai","topics":["tech_ai","business","society"]},
    ],
    # ---- SET 3 ----
    [
        {"source":"BBC","country":"UK","title":"London Court Sentences Former Minister in Historic Corruption Trial","summary":"A former cabinet minister was sentenced to prison for accepting bribes worth millions from construction firms. The judge called the case the most serious breach of public trust in a generation.","url":"https://www.bbc.com/news/uk-corruption-trial","topics":["politics","society","international"]},
        {"source":"CNN","country":"US","title":"Tesla Unveils Next-Generation Battery with 500-Mile Range","summary":"The electric vehicle maker revealed a new battery technology it claims doubles driving range while halving production cost. Analysts said the breakthrough could accelerate mass EV adoption.","url":"https://www.cnn.com/business/tesla-battery","topics":["tech_ai","business","energy"]},
        {"source":"AP News","country":"US","title":"Drought Drains Colorado River, Threatening Water Supply for 40 Million","summary":"The Colorado River fell to its lowest level on record, prompting federal authorities to mandate deeper water cuts across seven states. Farmers face the prospect of leaving fields unplanted.","url":"https://apnews.com/drought-colorado-river","topics":["climate","energy","society"]},
        {"source":"Reuters","country":"UK","title":"OPEC+ Agrees to Production Cut, Sending Oil Prices Soaring","summary":"The oil cartel and its allies announced a surprise reduction in output, causing crude prices to jump nearly 5 percent. Consumers face higher gasoline costs just as the driving season begins.","url":"https://www.reuters.com/business/opec-production-cut","topics":["economy","energy","international"]},
        {"source":"The Guardian","country":"UK","title":"University Researchers Create First Lab-Grown Human Embryo Model","summary":"Scientists grew structures that closely resemble human embryos without using sperm or eggs, raising ethical and scientific questions. The team said the models could revolutionize the study of early development.","url":"https://www.theguardian.com/science/lab-embryo","topics":["science","health","society"]},
    ],
    # ---- SET 4 ----
    [
        {"source":"BBC","country":"UK","title":"UK Announces Record Investment in Offshore Wind Power","summary":"The government approved the largest offshore wind project in national history, capable of powering over eight million homes. Environmental groups welcomed the move but called for faster grid upgrades.","url":"https://www.bbc.com/news/uk-offshore-wind","topics":["energy","climate","economy"]},
        {"source":"CNN","country":"US","title":"Supreme Court Upholds Key Provisions of Voting Rights Act","summary":"In a surprise ruling, the high court preserved core protections of the landmark civil rights law. Civil liberties groups called the decision a crucial victory for democratic participation.","url":"https://www.cnn.com/politics/voting-rights-ruling","topics":["politics","society","international"]},
        {"source":"AP News","country":"US","title":"CDC Warns of Rising Cases of Drug-Resistant Bacterial Infections","summary":"Health officials reported a sharp increase in infections caused by antimicrobial-resistant bacteria, particularly in hospitals. The agency urged facilities to strengthen infection control protocols.","url":"https://apnews.com/health/superbug-infections","topics":["health","science","society"]},
        {"source":"Reuters","country":"UK","title":"China and US Resume Trade Talks After Year-Long Freeze","summary":"Senior officials from both countries met for the first time in over a year, discussing tariffs, technology transfers, and market access. Both sides described the atmosphere as constructive but cautioned a deal was far off.","url":"https://www.reuters.com/world/us-china-trade","topics":["international","economy","business"]},
        {"source":"The Guardian","country":"UK","title":"Archaeologists Discover Ancient Library Buried Under Roman Ruins","summary":"A team unearthed hundreds of papyrus scrolls in a previously unexplored chamber near Pompeii. Researchers said the texts could contain lost works of Greek and Roman philosophy.","url":"https://www.theguardian.com/science/pompeii-scrolls","topics":["science","education","international"]},
    ],
    # ---- SET 5 ----
    [
        {"source":"BBC","country":"UK","title":"Parliament Rejects Prime Minister's Education Reform Bill","summary":"Lawmakers voted down sweeping changes to school funding and curriculum standards in a major defeat for the government. The prime minister said she would revise the legislation and bring it back for another vote.","url":"https://www.bbc.com/news/uk-education-reform","topics":["education","politics","society"]},
        {"source":"CNN","country":"US","title":"Major Automaker Recalls Two Million Vehicles Over Software Defect","summary":"The car manufacturer issued one of its largest recalls ever, warning that a software glitch could cause the braking system to malfunction. No injuries have been reported, but regulators demanded an investigation.","url":"https://www.cnn.com/business/auto-recall-software","topics":["tech_ai","business","society"]},
        {"source":"AP News","country":"US","title":"Tropical Storm Makes Landfall, Bringing Catastrophic Flooding","summary":"The storm slammed into the Gulf Coast with winds exceeding 80 miles per hour, dumping over two feet of rain in some areas. Rescue teams worked through the night to reach stranded residents.","url":"https://apnews.com/tropical-storm-flooding","topics":["climate","international","health"]},
        {"source":"Reuters","country":"UK","title":"Bank of England Holds Rates, Warns Inflation Battle Not Over","summary":"The central bank left its benchmark interest rate unchanged but struck a hawkish tone, suggesting that further tightening remained possible. Markets pared back expectations of early rate cuts.","url":"https://www.reuters.com/markets/boe-rates","topics":["economy","business","politics"]},
        {"source":"The Guardian","country":"UK","title":"Researchers Map Complete Genome of Endangered Species","summary":"Scientists have sequenced the full DNA of the Sumatran rhinoceros, identifying genetic factors behind its population decline. The data could guide breeding programs and conservation strategies.","url":"https://www.theguardian.com/science/rhino-genome","topics":["science","climate","health"]},
    ],
    # ---- SET 6 ----
    [
        {"source":"BBC","country":"UK","title":"UK Unemployment Falls to Near-Record Low Despite Economic Headwinds","summary":"The jobless rate dropped to its lowest level in decades, defying expectations of a broader slowdown. However, wage growth continued to lag behind inflation, squeezing household budgets.","url":"https://www.bbc.com/news/uk-unemployment","topics":["economy","society","business"]},
        {"source":"CNN","country":"US","title":"Senate Confirms New Ambassador to the United Nations","summary":"The upper chamber approved the president's nominee for UN ambassador in a largely bipartisan vote. The new envoy pledged to prioritize climate diplomacy and humanitarian coordination.","url":"https://www.cnn.com/politics/un-ambassador","topics":["politics","international","climate"]},
        {"source":"AP News","country":"US","title":"Researchers Find Microplastics in Human Brain Tissue","summary":"A new study detected plastic particles in brain tissue samples from dozens of donors, raising urgent questions about health effects. Scientists called for further research into how microplastics cross the blood-brain barrier.","url":"https://apnews.com/health/microplastics-brain","topics":["health","science","climate"]},
        {"source":"Reuters","country":"UK","title":"Global Shipping Giants Merge in Deal Reshaping Industry","summary":"Two of the world's largest container shipping companies announced a merger that would create the industry's biggest operator. Regulators in multiple jurisdictions signaled they would scrutinize the deal closely.","url":"https://www.reuters.com/business/shipping-merger","topics":["business","economy","international"]},
        {"source":"The Guardian","country":"UK","title":"Schools Roll Out Mandatory AI Literacy Curriculum","summary":"Education authorities introduced compulsory lessons on artificial intelligence for secondary students, covering both practical skills and ethical considerations. Teachers said they needed urgent training to deliver the new syllabus.","url":"https://www.theguardian.com/education/ai-literacy-schools","topics":["education","tech_ai","society"]},
    ],
    # ---- SET 7 ----
    [
        {"source":"BBC","country":"UK","title":"Energy Giants Post Record Profits Amid Consumer Price Pain","summary":"Major oil and gas companies reported bumper earnings while households struggled with energy bills. Politicians on all sides called for expanded windfall taxes on the sector.","url":"https://www.bbc.com/news/energy-profits","topics":["energy","economy","politics"]},
        {"source":"CNN","country":"US","title":"Federal Court Blocks State Law Restricting Social Media for Minors","summary":"A federal judge issued an injunction against a state law that would have banned users under 16 from social platforms, ruling it likely violated free speech protections. The state said it would appeal.","url":"https://www.cnn.com/technology/social-media-law","topics":["tech_ai","politics","society"]},
        {"source":"AP News","country":"US","title":"First Human Receives Experimental Gene Therapy for Sickle Cell Disease","summary":"A patient received a groundbreaking gene-editing treatment designed to cure the inherited blood disorder permanently. Doctors said they would monitor results closely for at least a year.","url":"https://apnews.com/health/gene-therapy-sickle-cell","topics":["health","science","tech_ai"]},
        {"source":"Reuters","country":"UK","title":"NATO Leaders Pledge Long-Term Military Support for Ukraine","summary":"Alliance members agreed on a framework for sustained defense assistance, including training and equipment commitments. The declaration stopped short of offering a formal membership timeline.","url":"https://www.reuters.com/world/nato-ukraine-support","topics":["international","politics","business"]},
        {"source":"The Guardian","country":"UK","title":"Premier League Clubs Report Surge in Revenue From Global Broadcasting","summary":"Top-flight football teams saw combined income reach record levels, driven by overseas television rights. However, the league warned that new regulations could threaten the financial model.","url":"https://www.theguardian.com/sport/premier-league-revenue","topics":["sports","business","international"]},
    ],
    # ---- SET 8 ----
    [
        {"source":"BBC","country":"UK","title":"Government Launches Review Into Social Media Algorithm Harms","summary":"The culture secretary ordered an independent inquiry into how recommendation algorithms on major platforms affect young users. The review could lead to new statutory duties for tech companies.","url":"https://www.bbc.com/news/tech-algorithm-review","topics":["tech_ai","politics","society"]},
        {"source":"CNN","country":"US","title":"Inflation Data Fuels Speculation of September Rate Cut","summary":"Core price growth slowed more than expected, strengthening the case for the central bank to begin easing policy. Bond yields tumbled and stock futures jumped on the news.","url":"https://www.cnn.com/economy/inflation-rate-cut","topics":["economy","business","politics"]},
        {"source":"AP News","country":"US","title":"Heat Dome Triggers Extreme Weather Alerts Across Central States","summary":"A massive heat dome settled over the Midwest, sending heat indices above 110 degrees. Meteorologists said the pattern could persist for a week, straining crops and livestock.","url":"https://apnews.com/heat-dome-central-states","topics":["climate","energy","health"]},
        {"source":"Reuters","country":"UK","title":"Major Retailer Files for Bankruptcy, Threatening 10,000 Jobs","summary":"One of the country's largest brick-and-mortar chains sought court protection from creditors after years of declining sales. Liquidation sales began immediately at hundreds of stores.","url":"https://www.reuters.com/business/retailer-bankruptcy","topics":["business","economy","society"]},
        {"source":"The Guardian","country":"UK","title":"Astronomers Detect Signal From Galaxy Born Near Dawn of Universe","summary":"Telescope observations captured radio emissions from a galaxy formed less than 300 million years after the Big Bang. The discovery pushes back the known timeline of early cosmic structure.","url":"https://www.theguardian.com/science/early-galaxy","topics":["science","tech_ai","international"]},
    ],
    # ---- SET 9 ----
    [
        {"source":"BBC","country":"UK","title":"New Public Transport Funding Aimed at Reducing Car Dependency","summary":"The transport secretary announced billions in new investment for buses and rail lines, particularly in underserved regions. The plan targets a 20 percent reduction in urban car journeys within a decade.","url":"https://www.bbc.com/news/uk-transport-funding","topics":["society","economy","climate"]},
        {"source":"CNN","country":"US","title":"Tech Giant Acquires AI Startup in Multi-Billion Dollar Deal","summary":"The industry leader agreed to purchase a prominent artificial intelligence company, accelerating the wave of consolidation in the sector. Antitrust regulators signaled they would review the transaction.","url":"https://www.cnn.com/business/ai-acquisition","topics":["tech_ai","business","politics"]},
        {"source":"AP News","country":"US","title":"CDC Issues Alert as Flu Season Arrives Early and Hits Hard","summary":"Influenza cases surged weeks ahead of the usual timeline, overwhelming some emergency departments. Officials urged the public to get vaccinated, noting ample supply this year.","url":"https://apnews.com/health/flu-season-early","topics":["health","society","science"]},
        {"source":"Reuters","country":"UK","title":"Developing Nations Walk Out of Trade Talks Over Agriculture Subsidies","summary":"Delegations from dozens of countries staged a dramatic walkout, accusing wealthy nations of stonewalling on farm subsidy reform. Negotiators scrambled to salvage the summit before it collapsed entirely.","url":"https://www.reuters.com/world/trade-talks-walkout","topics":["international","economy","politics"]},
        {"source":"The Guardian","country":"UK","title":"Olympic Committee Announces Five New Sports for 2032 Games","summary":"The governing body added five disciplines to the program for the Brisbane Olympics, including squash and flag football. The move aims to attract younger audiences and boost global viewership.","url":"https://www.theguardian.com/sport/olympics-new-sports","topics":["sports","international","society"]},
    ],
]

# ============================================================
# Auto mode: generates news from templates, no AI needed
# ============================================================
def auto_mode():
    """Generate today's news from built-in templates and inject.
    Idempotent: if today's news already exists (>=5 entries), skip injection.
    This prevents duplicate injection if the automation retries or runs twice."""
    from datetime import datetime, date
    import re

    today_str = datetime.now().strftime("%Y-%m-%d")
    day_of_year = datetime.now().timetuple().tm_yday

    # Idempotency guard: count today's LIVE news entries already in HTML
    # Must check source_type='live' specifically — otherwise if today's
    # automation hasn't run yet (0 live entries) but yesterday has >=5 entries,
    # the guard wrongly skips (today's auto never ran → 0 real news pushed).
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        _html = f.read()
    _live_pat = re.compile(
        r"date\s*:\s*['\"]" + re.escape(today_str) + r"['\"]"
        r".*?source_type\s*:\s*'live'", re.DOTALL)
    _existing_live = len(_live_pat.findall(_html))
    if _existing_live >= 5:
        print(f"AUTO SKIP: {today_str} already has {_existing_live} live entries. Not injecting again (idempotent guard).")
        _html = write_status(_html, "ok", f"✅ 今日已推送 {_existing_live} 篇新闻（{today_str}）")
        _html = write_run_log(_html, f"auto → 跳过：今日已有 {_existing_live} 篇（{today_str}）")
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(_html)
        return

    # 【严格真实】auto_mode 不再注入模板/虚构新闻（旧的 50 篇虚构头条已废弃）。
    # 任何页面展示的新闻必须来自实时抓取的真实来源。这里直接写"暂无当日新闻"状态，
    # 绝不伪造 BBC/CNN 标题与假链接。
    html = _html
    print(f"AUTO REFUSE: {today_str} no real news, skipping fabricated template injection.")
    html = write_status(html, "warn", f"⏳ 暂未获取到当日真实新闻（{today_str}），稍后自动重试")
    html = write_run_log(html, f"auto → 未取到真实新闻，跳过虚构模板（{today_str}）")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    return

    # ── 以下为废弃的虚构模板注入逻辑，保留仅作参考，永不执行 ──
    # Pick template set: cycle through 0-9 based on day_of_year
    set_idx = (day_of_year // 3) % len(NEWS_TEMPLATES)
    template_set = NEWS_TEMPLATES[set_idx]

    # Build articles with today's date
    articles = []
    for tmpl in template_set:
        article = {
            "date": today_str,
            "source": tmpl["source"],
            "country": tmpl["country"],
            "title": tmpl["title"],
            "summary": tmpl["summary"],
            "url": tmpl["url"],
            "topics": tmpl["topics"],
            "source_type": "template",  # offline placeholder, NOT real news
        }
        articles.append(article)

    # Load usage tracker
    tracker = load_tracker()

    # Auto-fill vocab, grammar, slang for each article
    for idx, article in enumerate(articles):
        topics = article.get("topics", ["politics", "economy"])

        # Pick 3 vocab words from matching topics
        vocab_picks = pick_vocab(topics, tracker, 3)
        article["vocabPoints"] = [v for _, v in vocab_picks]
        for _, v in vocab_picks:
            if v["word"] not in tracker["used_vocab"]:
                tracker["used_vocab"].append(v["word"])

        # Pick 1 grammar
        grammar = pick_grammar(tracker)
        article["grammarPoints"] = [grammar]
        if grammar["pattern"][:40] not in tracker["used_grammar"]:
            tracker["used_grammar"].append(grammar["pattern"][:40])

        # Pick 1 slang
        slang = pick_slang(tracker)
        article["slangPoints"] = [slang]
        if slang["term"] not in tracker["used_slang"]:
            tracker["used_slang"].append(slang["term"])

    # Trim tracker
    tracker["used_vocab"] = tracker["used_vocab"][-200:]
    tracker["used_grammar"] = tracker["used_grammar"][-100:]
    tracker["used_slang"] = tracker["used_slang"][-60:]
    tracker["last_date"] = today_str
    save_tracker(tracker)

    # Inject into HTML
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Insert news articles
    news_marker = "  return [\n"
    news_idx = html.find(news_marker)
    if news_idx == -1:
        news_marker = "  return ["
        news_idx = html.find(news_marker, html.find("function getDefaultNews"))

    if news_idx == -1:
        print("ERROR: Could not find getDefaultNews return array")
        sys.exit(1)

    insert_pos = news_idx + len(news_marker)
    news_block = f"    // ===== {today_str} =====\n"
    for idx, article in enumerate(articles):
        news_block += gen_news_js(article, idx) + "\n"

    html = html[:insert_pos] + "\n" + news_block + html[insert_pos:]

    # 2. Insert vocab entries
    vocab_end_marker = "  ];\n}\n\nfunction getDefaultGrammar"
    vocab_end_idx = html.find(vocab_end_marker)
    if vocab_end_idx == -1:
        print("ERROR: Could not find getDefaultVocab end")
        sys.exit(1)

    vocab_block = ""
    for idx, article in enumerate(articles):
        vocab_block += gen_vocab_js(article, idx) + "\n"

    html = html[:vocab_end_idx] + vocab_block + html[vocab_end_idx:]

    # 3. Insert grammar entries
    grammar_end_marker = "  ];\n}\n\nfunction getDefaultSettings"
    grammar_end_idx = html.find(grammar_end_marker)
    if grammar_end_idx == -1:
        print("ERROR: Could not find getDefaultGrammar end")
        sys.exit(1)

    grammar_block = ""
    for idx, article in enumerate(articles):
        grammar_block += gen_grammar_js(article, idx) + "\n"

    html = html[:grammar_end_idx] + grammar_block + html[grammar_end_idx:]

    # Write updated HTML (with push status bar + run log)
    html = write_status(html, "warn", f"⚠️ 离线备用内容已生成（{today_str}，非当日真实新闻）")
    html = write_run_log(html, f"auto → 离线备用：注入模板内容 {len(articles)} 篇（{today_str}，非真实新闻）")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    vocab_count = sum(len(a.get("vocabPoints", [])) for a in articles)
    grammar_count = sum(len(a.get("grammarPoints", [])) for a in articles)
    slang_count = sum(len(a.get("slangPoints", [])) for a in articles)

    print(f"AUTO SUCCESS: Injected {len(articles)} news + {vocab_count} vocab + {grammar_count} grammar + {slang_count} slang (date={today_str}, set={set_idx})")
    print("Titles:")
    for a in articles:
        print(f"  - [{a['source']}] {a['title']}")

def write_status(html, status_class, text):
    """Replace the push-status div content in HTML. Returns updated html."""
    status_regex = re.compile(r'<div class="push-status[^"]*" id="pushStatus">.*?</div>', re.DOTALL)
    new_block = f'<div class="push-status {status_class}" id="pushStatus">{text}</div>'
    if status_regex.search(html):
        return status_regex.sub(new_block, html, count=1)
    return html

RUN_LOG_CAP = 12

def write_run_log(html, entry):
    """Append a timestamped entry to the in-page auto-run log.

    The log lives INSIDE the HTML page, so it survives 499s: even if the AI's
    final chat message is killed, the deployed page shows exactly what ran.
    Keeps the last RUN_LOG_CAP entries. Creates the block if missing.
    """
    from datetime import datetime
    ts = datetime.now().strftime("%m-%d %H:%M:%S")
    item = f'<p class="run-log-item">[{ts}] {entry}</p>'

    container_re = re.compile(r'<div class="run-log" id="runLog">.*?</div>', re.DOTALL)
    m = container_re.search(html)
    if m:
        inner = m.group(0)
        items = re.findall(r'<p class="run-log-item">.*?</p>', inner, re.DOTALL)
        items.append(item)
        items = items[-RUN_LOG_CAP:]
        new_block = '<div class="run-log" id="runLog"><p class="run-log-title">📋 自动运行日志</p>' + "".join(items) + '</div>'
        return container_re.sub(lambda _: new_block, html, count=1)

    block = ('<div class="run-log" id="runLog"><p class="run-log-title">📋 自动运行日志</p>' + item + '</div>')
    push_re = re.compile(r'(<div class="push-status[^"]*" id="pushStatus">.*?</div>)', re.DOTALL)
    if push_re.search(html):
        return push_re.sub(lambda m2: m2.group(1) + "\n  " + block, html, count=1)
    return html

# ============================================================
# REAL news injection (source_type='live')
# ============================================================

def _norm_word(w):
    """Light lemmatization for matching article tokens to vocab bank words."""
    w = w.lower().strip("'-")
    if w.endswith("'s"):
        w = w[:-2]
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ied") and len(w) > 4:      # denied -> deny
        return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        if len(base) > 2 and base[-1] == base[-2]:  # banning -> ban
            base = base[:-1]
        return base
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if len(base) > 2 and base[-1] == base[-2]:  # banned -> ban, stopped -> stop
            base = base[:-1]
        return base
    if w.endswith("es") and len(w) > 3:
        return w[:-2]
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
        return w[:-1]
    return w


# ---- 从新闻正文提取（严格"跟着新闻学英语"模式）----

def _resolve_any_word(token):
    """结构自愈：对任意词，先词形还原到 base_dict，再查基础权威词典。

    解决"悬停缺失"的根因：此前词库全靠手工维护，新文章每出现一个新词就
    要人工补一条释义，永远追不上。这里让任何出现在新闻正文里的常用词，
    只要在 base_dict（由 HW_CORE 同步生成）里，就自动获得释义，覆盖是
    确定性的，不依赖词库有多大。

    返回 (word, definition) 或 None。
    """
    if not token or len(token) < 3:
        return None
    t = token.lower().strip("'-")
    if t.endswith("'s"):
        t = t[:-2]
    # 逐级尝试原形 / 词形还原候选，命中即返回
    cands = [t]
    if t.endswith("ies") and len(t) > 4:
        cands.append(t[:-3] + "y")
    if t.endswith("ied") and len(t) > 4:
        cands.append(t[:-3] + "y")
    if t.endswith("ing") and len(t) > 5:
        b = t[:-3]
        if len(b) > 2 and b[-1] == b[-2]:
            b = b[:-1]
        cands.append(b)          # admitting -> admit
        if b.endswith("e"):
            cands.append(b[:-1])  # creating -> creat? (handled by +e)
    if t.endswith("ed") and len(t) > 4:
        b = t[:-2]
        if len(b) > 2 and b[-1] == b[-2]:
            b = b[:-1]
        cands.append(b)
        cands.append(t[:-1])     # stopped -> stop(p) -> stop
    if t.endswith("es") and len(t) > 3:
        cands.append(t[:-2])
        cands.append(t[:-1])     # classes -> class -> class
    if t.endswith("s") and len(t) > 3 and not t.endswith("ss"):
        cands.append(t[:-1])     # shops -> shop
    if t.endswith("ly") and len(t) > 4:
        cands.append(t[:-2])     # quickly -> quick
    # 双写+e 回退：nodding -> nod(d?) ; broader -> broad
    if t.endswith("er") and len(t) > 4:
        cands.append(t[:-2])
    for c in cands:
        if c in _BASE_DICT:
            return c, _BASE_DICT[c]
    return None


def _gen_fallback(s):
    """为自愈词生成一个简单例句（取自新闻标题/摘要或空占位）。"""
    if not s:
        return ""
    s = s.strip()
    return s if len(s) <= 90 else s[:87] + "..."


# 结构自愈分支里跳过的高频虚词/弱教学词（页面端仍会通过 HW_FUNC 悬停，
# 只是不作为"每日生词"的教学选词）
_COMMON_STOP = set("""while which whose whom when where why what who how if
unless whether though although because although than then there here this that
these those some any many much few both each every all enough half least more
most very just only even still already again almost nearly never often always
usually sometimes soon now also about after before over under between among
during against from by as into through across along toward without within near
behind and or but so such same other else both too up down out in on at to for
with of a an the is are was were be been being will would can could should may
might must shall have has had do does did not no yes say says said get got make
take go goes come know think see look want use find give ask tell work call try
let keep help talk turn start end seem become feel put mean show add open close
live hold bring set sit run walk read write learn play pay send build buy
people man woman child day week month year time way world country home family
life part group number thing fact reason question word name place area street
school student teacher friend war peace law rule order plan idea message news
story report side north south east west
one two three four five six seven eight nine ten eleven twelve thirteen fourteen
fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty
seventy eighty ninety hundred thousand million billion first second third fourth
fifth sixth seventh eighth ninth tenth
# —— 低频却过于普通/抽象的教学弱词（不适合作为新闻精选词汇，仅保留页面悬停）——
rapid mass big media action terror describe official scenario migrant succession
throne hurricane survivor victim dozen rescue quake tremor toll rubble debris
evacuate shelter relief funding agency council minister spokesman interior foreign
brief moment current within recent previous soon early late morning afternoon
powerful strong weak major central main key large small heavy light full empty new old
another other further several many continue continue search find show make take give bring
turn call ask tell see look move reach rise fall grow drop halt stop start begin end
saturday sunday monday tuesday wednesday thursday friday week century month hour second
""".split())


def _merged_bank():
    """VOCAB_BANK（主题词库）+ EXTRA_DICT（大词库）合并，返回 word -> entry。"""
    bank = {}
    for _t, words in VOCAB_BANK.items():
        for v in words:
            bank.setdefault(v["word"].lower(), v)
    for w, (ph, cn, ex) in EXTRA_DICT.items():
        bank.setdefault(w.lower(), {"word": w, "phonetic": ph, "definition": cn, "example": ex})
    return bank


def match_vocab_from_text(text, count=3, tracker=None, exclude=None, title=None, summary=None):
    """Pick vocab words from the dictionary that ACTUALLY appear in the real
    article text (title + summary). Only words present in the text are
    returned — no unrelated fills. Longer (usually harder) words win."""
    if not text:
        return []
    bank = _merged_bank()

    banned = set(exclude or ())
    if tracker:
        # 文本驱动提取模式下防重复窗口缩短到 ~3 天（45 词）：
        # 真实新闻里的词隔几天重现是正常现象，不该硬禁
        banned |= set(tracker["used_vocab"][-45:] if tracker["used_vocab"] else [])

    # 短语动词/习语已被 slang 提取，词汇层跳过
    phrasal_words = set()
    for p in PHRASAL_BANK:
        for w in p.split():
            phrasal_words.add(w)

    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text.lower())
    matched, seen = [], set()
    for tok in tokens:
        # 尝试原形 / 去词缀 / 去词缀+e（creating→create）多种候选
        v = None
        for cand in (tok, _norm_word(tok), _norm_word(tok) + "e"):
            v = bank.get(cand)
            if v:
                break
        w = None
        if v:
            w = v["word"].lower()
            # 过于普通/抽象的教学弱词即使命中词库也不选作教学词（页面悬停仍在）
            if w in _COMMON_STOP:
                continue
            # example1 始终优先用“新闻原句”（用户要求：第一例句来自新闻原文），
            # 新闻句子里能找到该词就替换词库自带的 canned 例句；
            # 原 canned 例句暂存到 _bank_example 供 example2 复用（保证两条例句不同）。
            news_ex = _find_news_sentence(v["word"], title or "", summary or "")
            if news_ex:
                v = dict(v)  # 不改动词库原对象
                v["_bank_example"] = v.get("example", "")
                v["example"] = news_ex
        elif _BASE_DICT and "-" not in tok and "'" not in tok:
            # 结构自愈：词库未命中时，查权威基础词典（HW_CORE 同步生成）
            resolved = _resolve_any_word(tok)
            if resolved:
                cword, cdef = resolved
                # 高频虚词/弱教学词跳过（页面端仍会悬停，只是不作教学选词）
                if cword in _COMMON_STOP:
                    continue
                # 用新闻上下文生成例句，缺失的释义由 base_dict 兜底
                ex = _find_news_sentence(cword, title or "", summary or "") or _gen_fallback(text)
                v = {"word": cword, "phonetic": "", "definition": cdef, "example": ex}
                w = cword
        if v and w:
            if w in seen or w in banned or w in phrasal_words:
                continue
            matched.append(v)
            seen.add(w)
    # 优先长词（更难、更有学习价值），保持文本出现顺序为次序
    matched.sort(key=lambda v: -len(v["word"]))
    # 补齐英文释义（en_def）与扩展例句（example2），供详情页第二条展示
    for v in matched[:count]:
        v.setdefault("example2", _example2_for_vocab(v.get("word", ""), v))
        if not v.get("en_def"):
            # 优先拆分 definition 中的英文片段（'中文；英文gloss'），否则查表
            _cn, _en = _split_cn_en(v.get("definition", ""))
            if not _en:
                _en = _en_gloss_for(v.get("word", ""))
            if _en:
                # 仅当成功拆出英文时才改写 definition（去掉冗余英文，界面中文更清爽）
                if _cn and _cn != v.get("definition", ""):
                    v["definition"] = _cn
                v["en_def"] = _en
    return matched[:count]


def _find_news_sentence(word, title, summary):
    """Locate the actual sentence (from title/summary) containing `word`.
    Used as example #1 (新闻原句) in detail view."""
    # Join title and summary with a period so they split into real sentences
    # (a title never ends with a period, so otherwise title+summary become one
    # 200-char run-on that's useless as a "sentence").
    title = (title or "").strip()
    summary = (summary or "").strip()
    sep = ". " if title and not title.endswith((".", "!", "?")) else " "
    full = (title + sep + summary).strip() if (title or summary) else ""
    if not full:
        return ""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full) if len(s.strip()) > 8]
    target = word.lower().strip()
    # 1) lemma-token match in each sentence (title sentence checked first)
    for s in sents:
        toks = set(re.findall(r"[A-Za-z][A-Za-z'\-]*", s.lower()))
        for cand in (target, _norm_word(target), _norm_word(target) + "e"):
            if cand and cand in toks:
                return s[:220]
    # 2) substring fallback (phrases, inflections)
    for s in sents:
        if target in s.lower():
            return s[:220]
    # 3) give the title/summary head as last resort
    return full[:220]


# 每种语法模式的通用扩展例句（详情页第二条 example2）
GRAMMAR_GENERIC_EXAMPLES = {
    "被动语态 (Passive Voice)": "The bridge was built in 1932 and is still used by thousands of commuters every day.",
    "间接引语 / 转述动词 (Reported Speech)": "She told reporters (that) the deal had already been signed.",
    "定语从句 (Relative Clause)": "The scientist who developed the vaccine won the Nobel Prize.",
    "现在完成时 (Present Perfect)": "Prices have fallen sharply since January, and analysts expect the trend to continue.",
    "比较结构 (Comparatives)": "Inflation is now higher than at any point in the last decade.",
    "条件句 (Conditional)": "If the strike continues into next week, hundreds of flights will be cancelled.",
    "将来表达 (Future: will / going to)": "Officials said the new regulation will take effect from March.",
    "分词作状语 (Participle Clauses)": "Citing safety concerns, the airline grounded all its planes overnight.",
    "as 引导的时间/原因从句": "As the talks resumed, officials expressed cautious optimism.",
    "动名词作主语 (Gerund Subject)": "Building trust takes years, but losing it takes only a moment.",
    "despite / amid + 名词（让步/背景状语）": "Despite the setbacks, the team completed the project on time.",
    "不定式表目的 (Infinitive of Purpose)": "The central bank cut interest rates to stimulate growth.",
    "最高级 (Superlatives)": "It was the worst flood the region had seen in a century.",
    "新闻标题体 (Headline Grammar)": "President signs historic climate bill（标题用一般现在时 = 已发生的事，正文写 has signed）",
    "分词作定语 (-ing Participle Modifier)": "The rising cost of living is squeezing household budgets across the country.",
}

# 语法点英文释义（详情页第二条：English explanation，补充中文解释）
GRAMMAR_EN = {
    "被动语态 (Passive Voice)": "The passive voice emphasizes the action or its receiver rather than the doer: be + past participle. Used heavily in news when the doer is unknown or less important. The agent can be added with 'by' or omitted entirely.",
    "间接引语 / 转述动词 (Reported Speech)": "Reported (indirect) speech reports what someone said without using their exact words, typically with a reporting verb (said, told, added) and a tense shift: 'She said she was leaving.'",
    "定语从句 (Relative Clause)": "A relative clause modifies a noun using who (people), which (things), or that (both). When the relative pronoun is the object it can be omitted: 'the law (that) the Senate passed'.",
    "现在完成时 (Present Perfect)": "The present perfect (have/has + past participle) links a past action to the present moment. Used when the exact time is not given or the result still matters now: 'Prices have fallen sharply.'",
    "比较结构 (Comparatives)": "Comparatives compare two things using -er/more + than. Common in news for economic and social comparisons: 'Inflation is higher than a year ago.'",
    "条件句 (Conditional)": "Conditionals express conditions and results. The first conditional (if + present, will) is used for real future possibilities. Common in policy and economic news.",
    "将来表达 (Future: will / going to)": "English marks the future with 'will' (spontaneous decisions, predictions) or 'going to' (plans, intentions). News uses 'will' for official decisions: 'The president will announce the plan.'",
    "分词作状语 (Participle Clauses)": "A participle clause uses an -ing or -ed form to add background information to a main clause, making sentences concise and formal: 'Citing safety concerns, the airline grounded its planes.'",
    "as 引导的时间/原因从句": "'As' introduces a clause of time ('as the talks resumed') or reason ('as demand fell'). It gives background and connects two events in time.",
    "动名词作主语 (Gerund Subject)": "A gerund (-ing verb used as a noun) can be the subject of a sentence: 'Building trust takes years.' Common in formal and academic writing.",
    "despite / amid + 名词（让步/背景状语）": "'Despite' (showing contrast) and 'amid' (showing the surrounding situation) are followed by a noun phrase, not a full clause: 'Despite the setbacks, they pressed on.'",
    "不定式表目的 (Infinitive of Purpose)": "'to + base verb' expresses purpose or intention: 'The bank cut rates to stimulate growth.' Very common in policy and business news.",
    "最高级 (Superlatives)": "Superlatives (the -est / the most) describe the highest degree among three or more: 'It was the worst flood in a century.' Used for dramatic claims in headlines.",
    "新闻标题体 (Headline Grammar)": "Headlines compress language: they often omit articles and 'be' verbs, use the simple present for past events, and use 'to + infinitive' for the future: 'PM to visit Japan.'",
    "分词作定语 (-ing Participle Modifier)": "A present participle (-ing) used before a noun acts like an adjective describing that noun, short for 'which is/are ...ing': 'the rising cost of living.'",
}

# 常见俚语/短语动词的通用扩展例句（详情页第二条 example2；缺省时回退到释义中的英文搭配）
PHRASAL_EXAMPLES = {
    "call for": "Protesters called for the minister's immediate resignation.",
    "carry out": "The military carried out a series of airstrikes overnight.",
    "crack down": "Police have cracked down hard on illegal street racing.",
    "roll out": "The company will roll out the new payment system next month.",
    "kick off": "The summit kicked off with a speech by the host president.",
    "weigh in": "Several senators weighed in on the controversy yesterday.",
    "step down": "The CEO stepped down after the scandal broke.",
    "back down": "The government refused to back down over the new tax.",
    "push for": "Unions are pushing for a double-digit pay rise.",
    "point to": "All the evidence points to a premeditated attack.",
    "lead to": "The shortage led to panic buying in several cities.",
    "deal with": "Ministers met to discuss how to deal with the crisis.",
    "hold talks": "The two leaders held talks behind closed doors.",
    "shore up": "Emergency funds were released to shore up the banking system.",
    "ramp up": "Factories are ramping up production to meet demand.",
    "lay off": "The airline laid off 2,000 workers during the downturn.",
    "opt for": "Faced with delays, many commuters opted for the train.",
    "forge ahead": "The city is forging ahead with its redevelopment plans.",
    "stand down": "Troops were stood down after the ceasefire held.",
    "hit back": "The president hit back at his critics in a late-night post.",
    "pull out": "The sponsor pulled out of the deal at the last minute.",
    "walk out": "Delegates walked out of the session in protest.",
    "wipe out": "The tsunami wiped out entire coastal villages.",
    "draw on": "The report draws on data from over 40 countries.",
    "brace for": "Residents are bracing for another round of storms.",
    "grapple with": "Policymakers are still grappling with rising inflation.",
    "fend off": "The champion fended off a strong challenge in the final.",
    "stave off": "Emergency loans helped stave off bankruptcy.",
    "ride out": "Many small firms managed to ride out the recession.",
    "weather the storm": "The airline weathered the storm and returned to profit.",
    "in the wake of": "Fuel prices surged in the wake of the conflict.",
    "on the brink of": "The country was on the brink of civil war.",
    "on the verge of": "The airline is on the verge of collapse.",
    "in a bid to": "Taxes were cut in a bid to revive the economy.",
    "in an effort to": "Sanctions were eased in an effort to restart talks.",
    "under fire": "The agency came under fire over its slow response.",
    "come under fire": "The minister came under fire for his remarks.",
    "gain traction": "The protest movement quickly gained traction online.",
    "take a toll": "Years of war have taken a heavy toll on civilians.",
    "bear the brunt": "Coastal towns bore the brunt of the hurricane.",
    "make headway": "Negotiators say they are finally making headway.",
    "fall short": "Profits fell short of market expectations.",
    "double down": "Instead of apologising, he doubled down on his claim.",
    "walk back": "The aide later walked back the controversial statement.",
    "press ahead": "Officials pressed ahead with the project despite objections.",
    "hang in the balance": "Thousands of jobs hang in the balance tonight.",
    "up in the air": "The date of the election is still up in the air.",
    "on the table": "A compromise deal is now on the table.",
    "behind bars": "He spent five years behind bars for fraud.",
    "face the music": "The executives must face the music for their decisions.",
    "cast doubt on": "The leak cast doubt on the official death toll.",
    "shed light on": "The documents shed new light on the decision.",
    "keep at bay": "Vaccines helped keep the outbreak at bay.",
    "iron out": "Officials are still ironing out the final details.",
    "whip up": "Rival groups whipped up anger on social media.",
    "fan the flames": "The remarks fanned the flames of unrest.",
    "pass the buck": "Officials passed the buck instead of taking responsibility.",
    "turn the tide": "A late goal turned the tide of the match.",
    "turn a blind eye": "Regulators turned a blind eye to the abuses for years.",
    "turn up the heat": "Washington is turning up the heat on Beijing.",
    "ratchet up": "Both sides continue to ratchet up sanctions.",
    "beef up": "Police beefed up security ahead of the parade.",
    "prop up": "Subsidies were introduced to prop up ailing industries.",
    "cash in on": "Retailers are cashing in on the holiday rush.",
    "buy time": "The delay was designed to buy time for negotiations.",
    "write off": "The bank wrote off millions in bad loans.",
    "rule out": "Officials refused to rule out further strikes.",
    "roll back": "Campaigners want to roll back the new restrictions.",
    "clamp down on": "Authorities clamped down on unlicensed vendors.",
    "all but": "The insurgency has all but collapsed in recent months.",
    "in short supply": "Fuel and medicine remain in short supply.",
    "in high demand": "Skilled engineers are in high demand.",
    "silver lining": "The one silver lining is that unemployment has fallen.",
    "uphill battle": "Reforming the system remains an uphill battle.",
}

def _slang_generic_example(term, meaning):
    """example2 for slang: prefer PHRASAL_EXAMPLES, else reuse the English
    collocation embedded in the gloss (e.g. 'call for reforms 呼吁改革'),
    else generate a neutral news-style sentence."""
    if term in PHRASAL_EXAMPLES:
        return PHRASAL_EXAMPLES[term]
    m = re.search(r"[（(]([^）)]*?[A-Za-z][^）)]*?)[）)]", meaning or "")
    if m:
        frag = m.group(1).strip()
        en = re.match(r"[A-Za-z][A-Za-z' ,\-]*", frag)
        if en and len(en.group(0).strip()) > 2:
            return "常用搭配：" + en.group(0).strip()
    # 兜底：生成一条中性的新闻语境例句（保证 example2 永不为空；不再“自我指涉”）
    term_l = term.lower().strip()
    tpls = [
        "The latest report once again highlights '{t}' in its coverage.",
        "Analysts say '{t}' is being used more often in official statements this week.",
        "In today's headlines, '{t}' features prominently in the coverage.",
    ]
    key = sum(ord(c) for c in term_l) % len(tpls)
    return tpls[key].replace("{t}", term)


def _pick_phrasal(tracker, used_terms=None):
    """兜底：从 PHRASAL_BANK 挑一个短语（避免近 20 条重复），优先挑带真实例句的
    （PHRASAL_EXAMPLES 覆盖），保证 example2 是一条完整的英文新闻语境句而不是
    自我指涉的元描述。用于正文没出现俚语时仍给每篇 1 条俚语点。"""
    used = set(used_terms or ())
    prev = set(tracker["used_slang"][-20:] if tracker["used_slang"] else [])

    def _pool():
        # 优先：带真实例句的习语；且既不用过也不与近 20 条重复
        with_ex = [t for t in PHRASAL_BANK if t in PHRASAL_EXAMPLES]
        fresh = [t for t in with_ex if t not in used and t not in prev]
        if fresh:
            return fresh
        # 次选：全部带例句的，容许近期重复
        fresh = [t for t in with_ex if t not in used]
        if fresh:
            return fresh
        # 最后：任何未被本次用过的
        any_fresh = [t for t in PHRASAL_BANK if t not in used]
        if any_fresh:
            return any_fresh
        return list(PHRASAL_BANK)

    term = random.choice(_pool())
    meaning = PHRASAL_BANK[term]
    ex2 = _slang_generic_example(term, meaning)
    return {"term": term, "meaning": meaning,
            "en": _en_usage_for_slang(term, meaning, ex2),
            "example": "", "example2": ex2}


def extract_grammar_from_text(title, summary, used_patterns=None):
    """Detect a grammar pattern from the ACTUAL article sentences.
    Pass 1: prefer patterns not used yet today. Pass 2: allow reuse
    (different example sentence still teaches something new).
    Returns {pattern, explanation, example} or None."""
    import re as _re
    used = set(used_patterns or ())
    sentences = [s.strip() for s in _re.split(r"(?<=[.!?])\s+", (title or "") + ". " + (summary or "")) if len(s.strip()) > 10]
    for allow_used in (False, True):
        for name, expl, pat in GRAMMAR_PATTERNS:
            if not allow_used and name in used:
                continue
            rx = _re.compile(pat)
            for sent in sentences:
                m = rx.search(sent)
                if m:
                    return {"pattern": name, "explanation": expl,
                            "en": GRAMMAR_EN.get(name, ""),
                            "example": sent[:220],
                            "example2": GRAMMAR_GENERIC_EXAMPLES.get(name, "")}
    return None


def extract_slang_from_text(title, summary, used_terms=None):
    """Find a phrasal verb / idiom that ACTUALLY appears in the article text.
    Returns {term, meaning, example(新闻原句), example2(扩展用法)} or None."""
    text = ((title or "") + " " + (summary or "")).lower()
    used = set(used_terms or ())
    # 长短语优先匹配，避免 "call for" 抢走 "call for"类长语的子串
    for term in sorted(PHRASAL_BANK, key=len, reverse=True):
        if term in used:
            continue
        if term in text:
            ex2 = _slang_generic_example(term, PHRASAL_BANK[term])
            ex1 = _find_news_sentence(term, title, summary)
            return {"term": term, "meaning": PHRASAL_BANK[term],
                    "en": _en_usage_for_slang(term, PHRASAL_BANK[term], ex2),
                    "example": ex1, "example2": ex2}
    return None


def _headline_grammar_fallback(title):
    """兜底：仍从新闻本身出点 —— 标题含 -ing 词则讲分词作定语，否则讲标题体。"""
    m = re.search(r"\b([A-Za-z]+ing)\b", title or "")
    if m:
        return {
            "pattern": "分词作定语 (-ing Participle Modifier)",
            "explanation": f"标题中的 {m.group(1)} 是现在分词作定语，修饰后面的名词（相当于 which is/are …ing 的缩写）。这是新闻标题压缩句子的常用手法。",
            "example": (title or "")[:220],
        }
    return {
        "pattern": "新闻标题体 (Headline Grammar)",
        "explanation": "标题省略冠词与 be 动词、用一般现在时表过去事件。这是新闻英语的标志性语法。",
        "example": (title or "")[:220],
    }



def _remove_today_entries(html, today_str):
    """Remove today's previously-injected entries (news block + vocab + grammar)
    so live news can replace stale template placeholders. Returns (html, counts)."""
    date_key = today_str.replace("-", "")

    # 1. news block marked with "// ===== YYYY-MM-DD ====="
    pat_block = re.compile(
        r"\n\s*// ===== " + re.escape(today_str) + r" =====\n.*?(?=\n\s*// ===== |\n  \];)",
        re.DOTALL,
    )
    html, n1 = pat_block.subn("\n", html)
    # fallback: remove today's news objects even without the comment marker
    if n1 == 0:
        pat_obj = re.compile(
            r"\n\s*\{\s*id:\s*'n[^']*'\s*,\s*date:\s*['\"]" + re.escape(today_str) + r"['\"].*?\},\n",
            re.DOTALL,
        )
        html, n1 = pat_obj.subn("\n", html)

    # 2. vocab lines with id v_{datekey}_ (line-by-line, no DOTALL cross-line swallow)
    pat_v = re.compile(r"^[ \t]*\{id:'v_" + date_key + r"[^']*'.*?\},\n?", re.MULTILINE)
    html, n2 = pat_v.subn("\n", html)

    # 3. grammar lines with id g_{datekey}_
    pat_g = re.compile(r"^[ \t]*\{id:'g_" + date_key + r"[^']*'.*?\},\n?", re.MULTILINE)
    html, n3 = pat_g.subn("\n", html)

    return html, (n1, n2, n3)


def inject_live_news(json_path, force=False):
    """Inject REAL news (fetched via WebFetch from RSS) into the page.
    Articles get source_type='live'. Idempotent: skips if today already has
    >=5 live entries (unless force=True). Removes today's template
    placeholders first so real news always wins."""
    from datetime import datetime

    today_str = datetime.now().strftime("%Y-%m-%d")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        print(f"INJECT FAIL: cannot read {json_path}: {e}")
        return 1
    if not isinstance(items, list) or not items:
        print(f"INJECT FAIL: {json_path} contains no news items")
        return 1

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Idempotency: already >=5 live today?
    live_pat = re.compile(
        r"\{\s*id:\s*'n[^']*'\s*,\s*date:\s*['\"]" + re.escape(today_str) +
        r"['\"]" + r".*?source_type\s*:\s*'live'", re.DOTALL)
    live_count = len(live_pat.findall(html))
    if live_count >= 5 and not force:
        print(f"INJECT SKIP: {today_str} already has {live_count} live entries. Idempotent guard.")
        html = write_status(html, "ok", f"✅ 今日已推送 {live_count} 篇真实新闻（{today_str}）")
        html = write_run_log(html, f"inject → 跳过：今日已有 {live_count} 篇真实新闻（{today_str}）")
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return 0

    # Replace today's template placeholders with real news
    html, (n1, n2, n3) = _remove_today_entries(html, today_str)

    tracker = load_tracker()

    articles = []
    used_today = set()  # same-day hard dedup: a word appears at most once per day
    used_patterns_today = set()
    used_slang_today = set()
    for idx, item in enumerate(items[:5]):
        title = (item.get("title") or "").strip()
        link = (item.get("link") or "").strip()
        source = (item.get("source") or "News").strip()
        summary = (item.get("summary") or "").strip()
        # 正文全文（可选）：若抓取端提供了文章正文（body），则词汇/语法/俚语
        # 一律从【全文】提取，而不只是标题+导语摘要；正文也存入新闻对象供页面展示。
        body = (item.get("body") or "").strip()

        # 提词用的文本：优先全文，回退到标题+摘要
        extract_text = title + " " + (body or summary)
        extract_summary = body or summary  # 例句取全文原句

        # Vocab: STRICTLY from this article's own text (title + body 全文优先).
        # No unrelated fills — fewer points is fine, they are all real.
        vocab = match_vocab_from_text(extract_text, 3, tracker, exclude=used_today,
                                      title=title, summary=extract_summary)
        for v in vocab:
            used_today.add(v["word"])

        # Grammar: detected from the article's actual sentences
        grammar = extract_grammar_from_text(title, extract_summary, used_patterns_today)
        if grammar is None:
            grammar = _headline_grammar_fallback(title)
        # 补齐英文解析（en）——兜底分支可能缺省
        grammar.setdefault("en", GRAMMAR_EN.get(grammar.get("pattern", ""), ""))
        grammar.setdefault("example2", GRAMMAR_GENERIC_EXAMPLES.get(grammar.get("pattern", ""), ""))
        used_patterns_today.add(grammar["pattern"])

        # Slang/idiom: prefer terms that ACTUALLY appear; fall back to bank pick
        # so every article still gets one 俚语点 (per user requirement).
        slang = extract_slang_from_text(title, extract_summary, used_slang_today)
        if not slang:
            slang = _pick_phrasal(tracker, used_slang_today)
        slang_list = [slang]
        used_slang_today.add(slang["term"])

        article = {
            "date": today_str,
            "source": source,
            "country": "UK" if (source in ("BBC", "The Guardian", "Reuters", "The Telegraph") or "UK" in str(item.get("country", ""))) else "US",
            "title": title,
            "summary": summary,
            "body": body,  # 全文（可为空，页面据此决定展示摘要还是全文）
            "url": link,
            "source_type": "live",
            "vocabPoints": vocab,
            "grammarPoints": [grammar],
            "slangPoints": slang_list,
        }
        articles.append(article)

        for v in vocab:
            if v["word"] not in tracker["used_vocab"]:
                tracker["used_vocab"].append(v["word"])
        if grammar["pattern"][:40] not in tracker["used_grammar"]:
            tracker["used_grammar"].append(grammar["pattern"][:40])
        if slang and slang["term"] not in tracker["used_slang"]:
            tracker["used_slang"].append(slang["term"])

    tracker["used_vocab"] = tracker["used_vocab"][-200:]
    tracker["used_grammar"] = tracker["used_grammar"][-100:]
    tracker["used_slang"] = tracker["used_slang"][-60:]
    tracker["last_date"] = today_str
    save_tracker(tracker)

    # ---- inject news ----
    news_marker = "  return [\n"
    news_idx = html.find(news_marker)
    if news_idx == -1:
        news_marker = "  return ["
        news_idx = html.find(news_marker, html.find("function getDefaultNews"))
    if news_idx == -1:
        print("ERROR: Could not find getDefaultNews return array")
        sys.exit(1)
    insert_pos = news_idx + len(news_marker)
    news_block = f"    // ===== {today_str} =====\n"
    for idx, article in enumerate(articles):
        news_block += gen_news_js(article, idx) + "\n"
    html = html[:insert_pos] + "\n" + news_block + html[insert_pos:]

    # ---- inject vocab ----
    vocab_end_marker = "  ];\n}\n\nfunction getDefaultGrammar"
    vocab_end_idx = html.find(vocab_end_marker)
    if vocab_end_idx == -1:
        print("ERROR: Could not find getDefaultVocab end")
        sys.exit(1)
    vocab_block = ""
    for idx, article in enumerate(articles):
        vocab_block += gen_vocab_js(article, idx) + "\n"
    html = html[:vocab_end_idx] + vocab_block + html[vocab_end_idx:]

    # ---- inject grammar ----
    grammar_end_marker = "  ];\n}\n\nfunction getDefaultSettings"
    grammar_end_idx = html.find(grammar_end_marker)
    if grammar_end_idx == -1:
        print("ERROR: Could not find getDefaultGrammar end")
        sys.exit(1)
    grammar_block = ""
    for idx, article in enumerate(articles):
        grammar_block += gen_grammar_js(article, idx) + "\n"
    html = html[:grammar_end_idx] + grammar_block + html[grammar_end_idx:]

    sources = "、".join(sorted({a["source"] for a in articles}))
    html = write_status(html, "ok", f"✅ 今日已推送 {len(articles)} 篇真实新闻（{today_str}｜{sources}）")
    html = write_run_log(html, f"inject → 已注入 {len(articles)} 篇真实新闻（{today_str}｜{sources}）")
    # Auto-bump page version tag (vYYYYMMDD-N): increment N if a tag for
    # today already exists, so the number never goes backwards
    _ver_pat = re.compile(r'(id="pageVersionTag">)v(\d{8})-(\d+)')
    def _bump(m):
        d, n = m.group(2), int(m.group(3))
        new_d = today_str.replace("-", "")
        new_n = n + 1 if d == new_d else 1
        return m.group(1) + "v" + new_d + "-" + str(new_n)
    html = _ver_pat.sub(_bump, html)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"INJECT OK: {len(articles)} live articles injected for {today_str} from {sources}")
    print("Titles:")
    for a in articles:
        print(f"  - [{a['source']}] {a['title']}")
    return 0


def status_mode():
    """Report today's push status as structured text for automation to read.
    Exit codes: 0 = OK (>=5 live), 1 = MISSING (0 entries), 2 = TEMPLATE_ONLY."""
    from datetime import datetime

    today_str = datetime.now().strftime("%Y-%m-%d")
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    pat_obj = re.compile(
        r"\{\s*id:\s*'n[^']*'\s*,\s*date:\s*['\"]" + re.escape(today_str) + r"['\"].*?\}",
        re.DOTALL,
    )
    live = template = 0
    for m in pat_obj.finditer(html):
        seg = m.group(0)
        if "source_type: 'live'" in seg:
            live += 1
        else:
            template += 1
    total = live + template

    print(f"DATE={today_str}")
    print(f"LIVE={live}")
    print(f"TEMPLATE={template}")
    print(f"TOTAL={total}")
    if live >= 5:
        print("STATUS=OK")
        return 0
    if total >= 5:
        print("STATUS=TEMPLATE_ONLY")
        return 2
    print("STATUS=MISSING")
    return 1

def check_mode():
    """Pure check: does today's news exist in HTML? Writes push status to page.
    Runs in <1 second — cannot time out."""
    from datetime import datetime
    import re

    today_str = datetime.now().strftime("%Y-%m-%d")
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Match HTML format: date: '2026-08-12' or date: "2026-08-12" (no quotes around key)
    date_pattern = re.compile(r"date\s*:\s*['\"]" + re.escape(today_str) + r"['\"]")
    news_count = len(date_pattern.findall(html))

    if news_count >= 5:
        text = f"✅ 今日已推送 {news_count} 篇新闻（{today_str}）"
        print(f"CHECK PASS: {today_str} has {news_count} news entries (>= 5). Nothing to do.")
        html = write_status(html, "ok", text)
        html = write_run_log(html, f"check → 通过：今日已有 {news_count} 篇（{today_str}）")
    elif news_count >= 1:
        text = f"⚠️ 今日推送不完整，仅 {news_count} 篇（{today_str}），等待补推"
        print(f"CHECK WARN: {today_str} has only {news_count} news entries (< 5). Incomplete push detected.")
        html = write_status(html, "warn", text)
        html = write_run_log(html, f"check → 不完整：仅 {news_count} 篇（{today_str}）")
    else:
        text = f"❌ 今日未推送（{today_str}），稍后自动补推"
        print(f"CHECK FAIL: {today_str} has 0 news entries. Push failed — needs recovery.")
        html = write_status(html, "fail", text)
        html = write_run_log(html, f"check → 未推送：今日 0 篇（{today_str}）")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    return 0 if news_count >= 5 else (1 if news_count >= 1 else 2)

def ensure_mode():
    """Check then fix, real-news aware.
    Exit codes: 0 = has live news (OK, deploy); 1 = nothing existed, template
    fallback injected (offline placeholder — AI should still fetch real news);
    2 = template-only today (AI should fetch real news to replace it)."""
    from datetime import datetime
    import re

    today_str = datetime.now().strftime("%Y-%m-%d")
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    pat_obj = re.compile(
        r"\{\s*id:\s*'n[^']*'\s*,\s*date:\s*['\"]" + re.escape(today_str) + r"['\"].*?\}",
        re.DOTALL,
    )
    live = template = 0
    for m in pat_obj.finditer(html):
        seg = m.group(0)
        if "source_type: 'live'" in seg:
            live += 1
        else:
            template += 1
    total = live + template

    if live >= 5:
        text = f"✅ 今日已推送 {live} 篇真实新闻（{today_str}）"
        print(f"ENSURE OK: {today_str} has {live} live news entries. Nothing to do.")
        html = write_status(html, "ok", text)
        html = write_run_log(html, f"ensure → 今日已有 {live} 篇真实新闻（{today_str}）")
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return 0

    if total >= 5:
        text = f"⚠️ 今日仅离线备用内容（{today_str}），等待真实新闻注入"
        print(f"ENSURE TEMPLATE_ONLY: {today_str} has {template} template entries, 0 live.")
        html = write_status(html, "warn", text)
        html = write_run_log(html, f"ensure → 今日仅离线备用 {template} 篇，需真实新闻（{today_str}）")
        with open(HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html)
        return 2

    print(f"ENSURE TRIGGER: {today_str} has {total} entries (< 5).")
    # 【严格真实】不再注入任何模板/虚构新闻。宁可显示"今日暂无当日新闻",
    # 也绝不展示伪造的 BBC/CNN 标题与假链接。真实新闻只能来自实时抓取。
    text = f"⏳ 今日暂未获取到当日真实新闻（{today_str}），页面不显示虚构内容"
    html = write_status(html, "warn", text)
    html = write_run_log(html, f"ensure → 未取到真实新闻，不注入虚构内容（{today_str}）")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    return 1

def reextract_mode():
    """Re-extract vocab/grammar/slang for TODAY's live news from the article
    text already stored in the page. Used after extraction logic upgrades:
    removes today's entries, parses title/summary/url/source back out, and
    re-injects with the current extraction engine."""
    from datetime import datetime
    import json as _json

    today_str = datetime.now().strftime("%Y-%m-%d")
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    pat_obj = re.compile(
        r"\{\s*id:\s*'n[^']*'\s*,\s*date:\s*['\"]" + re.escape(today_str) + r"['\"].*?\},",
        re.DOTALL,
    )
    items = []
    for m in pat_obj.finditer(html):
        seg = m.group(0)
        if "source_type: 'live'" not in seg:
            continue
        def grab(key):
            mm = re.search(key + r":\s*'((?:[^'\\]|\\.)*)'", seg)
            return mm.group(1).replace("\\'", "'") if mm else ""
        items.append({
            "title": grab("title"),
            "summary": grab("summary"),
            "link": grab("url"),
            "source": grab("source"),
        })
    if not items:
        print(f"REEXTRACT FAIL: no live news found for {today_str}")
        return 1

    # Remove today's injected entries (news block + vocab + grammar)
    html, counts = _remove_today_entries(html, today_str)
    html = write_run_log(html, f"reextract → 重建今日学习点（{today_str}，{len(items)} 篇）")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    # Scrub the tracker so regeneration is not blocked by earlier runs:
    # every dictionary word that could be matched from TODAY's article text
    # is allowed again (same-day dedup still holds via used_today set).
    tracker = load_tracker()
    candidates = set()
    bank = _merged_bank()
    for it in items:
        text = ((it.get("title") or "") + " " + (it.get("summary") or "")).lower()
        for tok in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text):
            for cand in (tok, _norm_word(tok), _norm_word(tok) + "e"):
                if cand in bank:
                    candidates.add(bank[cand]["word"])
    if candidates:
        tracker["used_vocab"] = [w for w in tracker["used_vocab"] if w not in candidates]
        save_tracker(tracker)

    tmp = "/tmp/_reextract_news.json"
    with open(tmp, "w", encoding="utf-8") as f:
        _json.dump(items, f, ensure_ascii=False)
    return inject_live_news(tmp)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--auto":
        auto_mode()
    elif len(sys.argv) >= 2 and sys.argv[1] == "--check":
        sys.exit(check_mode())
    elif len(sys.argv) >= 2 and sys.argv[1] == "--ensure":
        sys.exit(ensure_mode())
    elif len(sys.argv) >= 2 and sys.argv[1] == "--status":
        sys.exit(status_mode())
    elif len(sys.argv) >= 2 and sys.argv[1] == "--inject":
        if len(sys.argv) < 3:
            print("Usage: python3 update_news.py --inject <live_news.json> [--force]")
            sys.exit(1)
        _force = "--force" in sys.argv[3:]
        sys.exit(inject_live_news(sys.argv[2], force=_force))
    elif len(sys.argv) >= 2 and sys.argv[1] == "--reextract":
        sys.exit(reextract_mode())
    else:
        main()
