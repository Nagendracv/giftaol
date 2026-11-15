import json
# Second batch of real searches, 2026-11-14 (same method as the first 20). own = rank of an Art of Living page/listing in the top 10, else None.
NEW = [
 ("meditation classes Halifax","Halifax","NS","learn meditation",False,None,["ca.srichinmoycentre.org","cademy.io","halifax.shambhala.org","canada.nalandabodhi.ca","halifax.shambhala.org","bookretreats.com","www.meetup.com","www.meetup.com","bookretreats.com","www.nobleprog.ca"]),
 ("meditation classes Saskatoon","Saskatoon","SK","learn meditation",False,None,["coursetakers.com","coursetakers.com","saskatoon.ctvnews.ca","www.discoversaskatoon.com","meditationsaskatoon.yolasite.com","broadwayhealthcollective3445.clinicsites.co","www.nobleprog.ca","discoversaskatoon.com","wellness.usask.ca","www.nobleprog.ca"]),
 ("meditation classes Regina","Regina","SK","learn meditation",False,None,["rpl.libnet.info","attend.reginalibrary.ca","attend.reginalibrary.ca","rpl.libnet.info","www.theknowledgeacademy.com","www.todocanada.ca","www.irest.org","www.theknowledgeacademy.com","haddock-bird-wy2f.squarespace.com","www.meetup.com"]),
 ("meditation classes Victoria BC","Victoria","BC","learn meditation",False,None,["www.eventbrite.ca","www.tickettailor.com","www.meetup.com","www.meetup.com","www.meetup.com","www.meetup.com","www.meetup.com","www.eventbrite.ca","www.meetup.com","www.meetup.com"]),
 ("meditation classes St. John's Newfoundland","St. John's","NL","learn meditation",False,None,["ca.srichinmoycentre.org","bookretreats.com","www.bookretreats.com","coursetakers.com","www.simpletix.com","www.simpletix.com","sites.google.com","www.simpletix.com","www.simpletix.com","thecalmplace.offeringtree.com"]),
 ("meditation classes Fredericton","Fredericton","NB","learn meditation",False,None,["fredericton.shambhala.org","business.frederictonchamber.ca","business.frederictonchamber.ca","fredericton.shambhala.org","www.zeffy.com","www.eventbrite.com.au","www.eventbrite.fi","amp.eventbrite.co.uk","www.eventbrite.de","rbmcdaniel.ca"]),
 ("meditation classes Charlottetown PEI","Charlottetown","PE","learn meditation",False,None,["canadahelps.org","canadahelps.org","buzzpei.com","canadahelps.org","buzzpei.com","buzzpei.com","buzzpei.com","happeningnext.com","islandtides.lakedesign.co","buzzpei.com"]),
 ("meditation classes Hamilton Ontario","Hamilton","ON","learn meditation",False,None,["bookretreats.com","coursetakers.com","www.eventbrite.dk","www.eventbrite.ca","www.eventbrite.ca","www.eventbrite.ca","www.eventbrite.ca","www.eventbrite.at","www.meetup.com","www.eventbrite.ca"]),
 ("meditation classes Kitchener Waterloo","Kitchener-Waterloo","ON","learn meditation",False,7,["www.eventbrite.co","communityedition.ca","www.eventbrite.com","www.eventbrite.com.au","calendar.kitchener.ca","www.eventbrite.ca","www.artofliving.org","www.eventbrite.ca","carespace.health","www.eventbrite.com.au"]),
 ("meditation classes Surrey BC","Surrey","BC","learn meditation",False,None,["www.nobleprog.ca","www.eventbrite.de","www.eventbrite.ca","www.eventbrite.ca","amp.eventbrite.be","www.eventbrite.ca","kriya.org","amp.eventbrite.dk","www.nobleprog.ca","www.eventbrite.com"]),
 ("meditation course Richmond Hill","Richmond Hill","ON","learn meditation",False,5,["www.eventbrite.ca","www.nobleprog.ca","www.eventbrite.ca","www.nobleprog.ca","www.artofliving.org","www.superprof.ca","www.artofliving.org","www.meetup.com","www.comfortlife.ca","www.meetup.com"]),
 ("meditation North Vancouver class","North Vancouver","BC","learn meditation",False,None,["globalnews.ca","www.gallerieswest.ca","www.straight.com","www.meetup.com","www.eventbrite.com.au","www.meetup.com","happeningnext.com","happeningnext.com","vancouver.shambhala.org","vancouver.shambhala.org"]),
 ("cours de méditation Québec ville","Québec City","QC","learn meditation (FR)",False,8,["211quebecregions.ca","info-aines-mauricie.cioc.ca","cancerquebec.ca","www.yellowpages.ca","cancerquebec.ca","montreal.ca","montreal.ca","artofliving.secure.retreat.guru","veq.ca","www.meetup.com"]),
 ("cours de méditation Laval","Laval","QC","learn meditation (FR)",False,None,["www.ulaval.ca"]*10),
 ("méditation Gatineau cours","Gatineau","QC","learn meditation (FR)",False,None,["www.meetup.com","app.amilia.com","www.meetup.com","formation-continue.uqo.ca","threebestrated.ca","bookretreats.com","cisss-outaouais.gouv.qc.ca","www.pagesjaunes.ca","shambhala.org","bookretreats.com"]),
 ("méditation Sherbrooke cours","Sherbrooke","QC","learn meditation (FR)",False,4,["www.usherbrooke.ca","amp.eventbrite.fi","www.usherbrooke.ca","www.artofliving.org","playsport.com","www.pagesjaunes.ca","fadoq.ca","www.eventbrite.co","www.artofliving.org","www.eventbrite.com.br"]),
 ("retraite de méditation Mauricie","Mauricie","QC","retreat (FR)",False,1,["retreat.guru"]*10),
 ("atelier respiration gestion du stress Montréal","Montreal","QC","stress (FR)",False,None,["montreal.ca","montreal.ca","montreal.ca","montreal.ca","montreal.ca","sante-mentale-jeunesse.usherbrooke.ca","openagenda.com","fondationjasminroy.com","sante-mentale-jeunesse.usherbrooke.ca","www.helloasso.com"]),
 ("meditation classes Kelowna","Kelowna","BC","learn meditation",False,None,["www.nobleprog.ca","www.amilia.com","www.amilia.com","kelowna.com","bookretreats.com","www.kelownanow.com","inspirehealth.ca","kelowna.com","bookretreats.com","www.theknowledgeacademy.com"]),
 ("meditation classes London Ontario","London ON","ON","learn meditation",False,None,["www.nobleprog.ca","www.eventbrite.ca","www.eventbrite.ca","www.psychologytoday.com","www.todocanada.ca","www.eventbrite.ca","coursetakers.com","www.eventbrite.com.au","meditateinlondon.org","www.eventbrite.com.au"]),
 ("meditation classes Brampton","Brampton","ON","learn meditation",False,None,["www.eventbrite.com.au","www.eventbrite.sg","amp.eventbrite.co.uk","amp.eventbrite.fi","amp.eventbrite.com","amp.eventbrite.co.uk","bookretreats.com","cnib.ca","meetup.com","wellspring.ca"]),
 ("meditation classes Markham","Markham","ON","learn meditation",False,2,["markham.bibliocommons.com","www.artofliving.org","www.meetup.com","www.eventbrite.pt","sop.utoronto.ca","markham.bibliocommons.com","playsport.com","www.meetup.com","forms.gle","events.yorku.ca"]),
 ("meditation classes Oakville Burlington","Oakville","ON","learn meditation",False,None,["halton.cioc.ca","halton.cioc.ca","hipinfo.cioc.ca","halton.cioc.ca","www.hipinfo.ca","www.hipinfo.ca","www.hipinfo.ca","www.hipinfo.ca","culturedays.ca","www.meetup.com"]),
 ("meditation classes Edmonton","Edmonton","AB","learn meditation",False,None,["barbarinoshair.yellowpages.ca","edmonton.shambhala.org","bookretreats.com","www.eventbrite.ca","coursetakers.com","amp.eventbrite.fi","www.eventbrite.fi","www.superprof.ca","eventbrite.dk","www.poyst.com"]),
 ("breathing course for anxiety Toronto","Toronto","ON","anxiety",False,6,["theseedlodge.secure.retreat.guru","theseedlodge.secure.retreat.guru","www.eventbrite.ca","yukon.cmha.ca","definitions.therapytoronto.ca","www.artofliving.org","happeningnext.com","mindisthemaster.com","mindisthemaster.com","mindisthemaster.com"]),
 ("breathwork class Vancouver","Vancouver","BC","breathwork",False,None,["www.eventbrite.com","www.eventbrite.com","www.tickettailor.com","www.tickettailor.com","carolyn-anne-budgell.squarespace.com","www.universe.com","www.liquidbreathwork.com","happeningnext.com","universe.com","www.eventbrite.ca"]),
 ("breathwork Calgary","Calgary","AB","breathwork",False,None,["www.eventbrite.com","www.eventbrite.ca","bookretreats.com","www.eventbrite.ca","www.eventbrite.com","www.tickettailor.com","www.tickettailor.com","www.meetup.com","coopercounselling.janeapp.com","bookretreats.com"]),
 ("stress management course Ottawa","Ottawa","ON","stress",False,None,["www.theknowledgeacademy.com","coursetakers.com","coursetakers.com","coursetakers.com","bilginc.com","theknowledgeacademy.com","www.nobleprog.ca","www.theknowledgeacademy.com","www.theknowledgeacademy.com","coursetakers.com"]),
 ("pranayama class Toronto","Toronto","ON","breathwork",False,None,["humber.ca","bookretreats.com","www.superprof.co.in","sites.google.com","news.uoguelph.ca","www.eventbrite.ca","www.evensi.com","www.airbnb.com","www.poyst.com","icccottawa.org"]),
 ("meditation classes Mississauga","Mississauga","ON","learn meditation",False,None,["www.eventbrite.ca","amp.eventbrite.fi","www.eventbrite.de","www.eventbrite.ca","mississauga.shambhala.org","www.eventbrite.it","www.meetup.com","www.theknowledgeacademy.com","www.eventbrite.com","www.meetup.com"]),
 ("meditation workshop for teens Canada","Canada","","teens",False,None,["globalnews.ca","globalnews.ca","liveandplay.calgary.ca","liveandplay.calgary.ca","mindfulnessstudies.com","childslife.ca","mindfulnessstudies.com","mindfulnessstudies.com","camps.ca","teachmag.com"]),
 ("yoga and meditation retreat Quebec","Quebec","QC","retreat",False,4,["monastere.ca","bookretreats.com","bookretreats.com","retreat.guru","bookretreats.com","bookretreats.com","www.bookretreats.com","www.bookretreats.com","bookretreats.com","bookretreats.com"]),
 ("Art of Living Montreal","Montreal","QC","branded",True,1,["www.artofliving.org","www.artofliving.org","www.artofliving.org","retreat.guru","www.artofliving.org","www.artofliving.org","globalnews.ca","www.artofliving.org","www.artofliving.org","www.artofliving.org"]),
 ("Art of Living Vancouver course","Vancouver","BC","branded",True,1,["www.eventbrite.ca","www.artofliving.org","www.artofliving.org","www.artofliving.org","globalnews.ca","www.artofliving.org","globalnews.ca","greyhound-pomegranate-pxh2.squarespace.com","www.meetup.com","www.artofliving.org"]),
]
PROV = {"Toronto":"ON","Vancouver":"BC","Montreal":"QC","Canada":"","Calgary":"AB","Ottawa":"ON","Edmonton":"AB","Mississauga":"ON","Winnipeg":"MB"}
NOTES = {
 "Kitchener-Waterloo":"Our Kitchener-Waterloo centre page came up.",
 "Richmond Hill":"Our Richmond Hill centre page came up.",
 "Markham":"Our Markham centre page came up at #2.",
 "Sherbrooke":"Our Sherbrooke centre page came up.",
 "Québec City":"Our Retreat Guru registration page came up.",
 "Mauricie":"The Canada Centre's retreat listings on Retreat Guru filled the results.",
}
p='data/audits/baseline-2026-11-14.json'
b=json.load(open(p))
for q in b["queries"]:
    q["province"]=PROV.get(q["city"],"")
    if q["city"]=="Canada": q["province"]=""
start=len(b["queries"])
for i,(qq,city,prov,intent,br,own,doms) in enumerate(NEW):
    rec={"id":f"q{start+i+1:02d}","query":qq,"city":city,"province":prov,"intent":intent,"branded":br,"engine":"web-search-grounding","resultDomains":doms,"ownRank":own,"mentioned":own is not None}
    if city in NOTES and own: rec["note"]=NOTES[city]
    if city=="Toronto" and own and intent=="anxiety": rec["note"]="Our Toronto Downtown centre page came up."
    if intent=="retreat" and own: rec["note"]="A Canada Centre retreat listed on Retreat Guru came up."
    b["queries"].append(rec)
b["method"]="Each question was sent to a live web search engine on 2026-11-14 (the step chatbots take before answering). We record the top 10 sources and whether an Art of Living page or listing is among them."
json.dump(b,open(p,'w'),separators=(',',':'),ensure_ascii=False)
qs=[{k:q[k] for k in ("id","query","city","province","intent","branded")} for q in b["queries"]]
json.dump({"note":"Real questions people ask about meditation and breathwork in Canada, in English and French. Unbranded ones measure discovery; branded ones are a control.","queries":qs},open('data/queries.json','w'),indent=1,ensure_ascii=False)
u=[q for q in b["queries"] if not q["branded"]]; br=[q for q in b["queries"] if q["branded"]]
print(len(b["queries"]), sum(q["mentioned"] for q in u),"/",len(u), sum(q["mentioned"] for q in br),"/",len(br))
