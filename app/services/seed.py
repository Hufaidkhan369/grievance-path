"""Seed the database with departments, routing keywords, and demo complaints."""
from ..database import db, init_db, fetch_one, now_utc

DEPARTMENTS = [
    {"code": "MCD", "name": "Municipal Corporation",
     "description": "Roads, garbage, street lights, drainage, sanitation, parks and encroachments in the city.",
     "contact_email": "mcd@grievancepath.in", "contact_phone": "1800-200-100", "color": "#0ea5e9"},
    {"code": "PWD", "name": "Public Works Department",
     "description": "Construction and maintenance of state roads, bridges, buildings and footpaths.",
     "contact_email": "pwd@grievancepath.in", "contact_phone": "1800-200-101", "color": "#f59e0b"},
    {"code": "EB", "name": "Electricity Board",
     "description": "Power cuts, electricity billing, transformers, voltage fluctuations and meter issues.",
     "contact_email": "eb@grievancepath.in", "contact_phone": "1912", "color": "#f43f5e"},
    {"code": "WS", "name": "Water Supply Department",
     "description": "Water shortage, pipeline leakage, contaminated water and water tanker requests.",
     "contact_email": "ws@grievancepath.in", "contact_phone": "1916", "color": "#06b6d4"},
    {"code": "POLICE", "name": "Police Department",
     "description": "Theft, crime, harassment, traffic violations, missing persons and law & order issues.",
     "contact_email": "police@grievancepath.in", "contact_phone": "100", "color": "#3b82f6"},
    {"code": "HEALTH", "name": "Public Health Department",
     "description": "Hospitals, ambulance services, disease outbreaks, sanitation and vaccination drives.",
     "contact_email": "health@grievancepath.in", "contact_phone": "108", "color": "#10b981"},
    {"code": "EDU", "name": "Education Department",
     "description": "Schools, colleges, scholarships, teachers, mid-day meals and RTE admission issues.",
     "contact_email": "edu@grievancepath.in", "contact_phone": "1800-200-102", "color": "#8b5cf6"},
    {"code": "TRANS", "name": "Transport Department",
     "description": "Public buses, metro, autos, railways, routes, fares and transport infrastructure.",
     "contact_email": "transport@grievancepath.in", "contact_phone": "1800-200-103", "color": "#14b8a6"},
    {"code": "ENV", "name": "Environment Department",
     "description": "Air pollution, deforestation, noise pollution, waste dumping and plastic ban violations.",
     "contact_email": "env@grievancepath.in", "contact_phone": "1800-200-104", "color": "#22c55e"},
    {"code": "CONSUMER", "name": "Consumer Affairs",
     "description": "Overcharging, defective products, false advertising, warranty and e-commerce disputes.",
     "contact_email": "consumer@grievancepath.in", "contact_phone": "1800-11-4000", "color": "#eab308"},
    {"code": "AGRI", "name": "Agriculture Department",
     "description": "Crops, fertiliser, subsidy, seeds, MSP, irrigation and farmer welfare schemes.",
     "contact_email": "agri@grievancepath.in", "contact_phone": "1800-200-105", "color": "#84cc16"},
    {"code": "REV", "name": "Revenue / Land Records",
     "description": "Land records, property registration, stamp duty, mutation and patta issues.",
     "contact_email": "revenue@grievancepath.in", "contact_phone": "1800-200-106", "color": "#a16207"},
    {"code": "TELECOM", "name": "Telecom Department",
     "description": "Mobile network, internet, broadband, signal issues and telecom service quality.",
     "contact_email": "telecom@grievancepath.in", "contact_phone": "1800-200-107", "color": "#6366f1"},
    {"code": "RATIONS", "name": "Food & Civil Supplies",
     "description": "Ration cards, PDS, fair price shops, LPG and food supply schemes.",
     "contact_email": "rations@grievancepath.in", "contact_phone": "1967", "color": "#d97706"},
    {"code": "DM", "name": "Disaster Management",
     "description": "Floods, cyclones, earthquakes, relief camps and emergency rescue operations.",
     "contact_email": "dm@grievancepath.in", "contact_phone": "1078", "color": "#ef4444"},
]

# (keyword, weight, is_negative)
KEYWORDS = {
    "MCD": [
        ("garbage", 3, 0), ("garbage collection", 4, 0), ("waste collection", 3, 0), ("rubbish", 3, 0),
        ("trash", 3, 0), ("litter", 2, 0), ("street light", 4, 0), ("streetlight", 4, 0), ("street lamp", 3, 0),
        ("road damaged", 3, 0), ("pothole", 4, 0), ("potholes", 4, 0), ("broken road", 3, 0), ("footpath", 3, 0),
        ("drainage", 4, 0), ("drain", 4, 0), ("sewage overflow", 4, 0), ("drainage blocked", 4, 0),
        ("stagnant water", 3, 0), ("sanitation", 3, 0), ("public toilet", 3, 0), ("toilet", 2, 0),
        ("encroachment", 4, 0), ("encroached", 3, 0), ("illegal encroachment", 4, 0), ("park", 2, 0),
        ("cattle menace", 3, 0), ("stray dog", 3, 0), ("stray cattle", 3, 0), ("dustbin", 3, 0),
        ("municipal", 3, 0), ("corporation", 2, 0), ("road", 2, 0), ("street", 2, 0),
        ("swachh", 2, 0), ("cleanliness", 2, 0), ("open drain", 3, 0), ("manhole", 4, 0),
        ("metro work", 1, 1), ("road transport", 1, 1), ("highway", 1, 1),
    ],
    "PWD": [
        ("bridge", 4, 0), ("bridge damaged", 5, 0), ("culvert", 4, 0), ("national highway", 4, 0),
        ("state highway", 4, 0), ("highway", 4, 0), ("road widening", 4, 0), ("new road", 3, 0),
        ("road repair", 4, 0), ("road construction", 4, 0), ("broken road", 3, 0), ("road", 2, 0),
        ("pwd", 4, 0), ("public works", 4, 0), ("government building", 3, 0), ("district road", 3, 0),
        ("underpass", 3, 0), ("flyover", 3, 0), ("road marking", 3, 0), ("speed breaker", 2, 0),
        ("street light", 1, 1), ("garbage", 1, 1), ("electricity", 1, 1),
    ],
    "EB": [
        ("power cut", 5, 0), ("electricity", 4, 0), ("electric", 3, 0), ("power outage", 5, 0),
        ("load shedding", 5, 0), ("transformer", 5, 0), ("voltage", 4, 0), ("fluctuation", 2, 0),
        ("electricity bill", 5, 0), ("power bill", 5, 0), ("billing", 2, 0), ("meter", 4, 0),
        ("meter reading", 4, 0), ("power supply", 4, 0), ("electricity connection", 4, 0), ("current", 3, 0),
        ("wire", 3, 0), ("power line", 4, 0), ("pole", 3, 0), ("electric pole", 4, 0),
        ("short circuit", 4, 0), ("tripping", 4, 0), ("fuse", 2, 0), ("eb office", 3, 0),
        ("inverter", 1, 1), ("water", 1, 1), ("street light", 1, 1),
    ],
    "WS": [
        ("water supply", 4, 0), ("water shortage", 5, 0), ("no water", 5, 0), ("water problem", 4, 0),
        ("water leakage", 5, 0), ("leaking pipe", 5, 0), ("pipeline", 4, 0), ("pipeline burst", 5, 0),
        ("contaminated water", 5, 0), ("dirty water", 5, 0), ("water pollution", 4, 0), ("tanker", 4, 0),
        ("water tanker", 4, 0), ("drinking water", 4, 0), ("borewell", 4, 0), ("bore well", 4, 0),
        ("water pressure", 4, 0), ("tap", 3, 0), ("water connection", 4, 0), ("water bill", 3, 0),
        ("ground water", 3, 0), ("supply", 2, 0), ("water", 3, 0),
        ("electricity", 1, 1), ("power", 1, 1),
    ],
    "POLICE": [
        ("theft", 5, 0), ("stolen", 5, 0), ("robbery", 5, 0), ("burglary", 5, 0), ("house break", 4, 0),
        ("harassment", 5, 0), ("molestation", 5, 0), ("assault", 5, 0), ("beaten", 4, 0), ("beating", 4, 0),
        ("threat", 4, 0), ("threatened", 4, 0), ("extortion", 5, 0), ("fight", 3, 0), ("crime", 5, 0),
        ("criminal", 5, 0), ("missing person", 5, 0), ("kidnapping", 5, 0), ("kidnap", 5, 0), ("chain snatching", 5, 0),
        ("traffic violation", 4, 0), ("traffic signal", 3, 0), ("rash driving", 4, 0), ("speeding", 3, 0),
        ("drunk driving", 4, 0), ("drunk driving", 4, 0), ("law and order", 5, 0), ("law & order", 5, 0),
        ("police", 4, 0), ("complaint", 2, 0), ("cyber crime", 4, 0), ("fraud", 3, 0), ("scam", 3, 0),
        ("cheated", 3, 0), ("cheating", 3, 0), ("gambling", 4, 0), ("gaming", 1, 1),
        ("consumer", 1, 1), ("overcharging", 1, 1),
    ],
    "HEALTH": [
        ("hospital", 5, 0), ("government hospital", 5, 0), ("hospital staff", 4, 0), ("doctor", 4, 0),
        ("ambulance", 5, 0), ("emergency", 3, 0), ("patient", 3, 0), ("medicines", 4, 0), ("medicine", 3, 0),
        ("vaccination", 5, 0), ("vaccine", 5, 0), ("dengue", 5, 0), ("malaria", 5, 0), ("fever", 3, 0),
        ("outbreak", 5, 0), ("epidemic", 5, 0), ("chikungunya", 5, 0), ("health centre", 4, 0),
        ("primary health centre", 5, 0), ("phc", 4, 0), ("medical", 3, 0), ("maternity", 4, 0),
        ("surgery", 3, 0), ("blood", 3, 0), ("blood bank", 4, 0), ("diarrhoea", 4, 0), ("cholera", 5, 0),
        ("mosquito", 3, 0), ("breeding", 2, 0), ("garbage", 1, 1), ("sewage", 1, 1),
    ],
    "EDU": [
        ("school", 5, 0), ("school building", 4, 0), ("teacher", 4, 0), ("teachers", 4, 0), ("student", 3, 0),
        ("students", 3, 0), ("college", 4, 0), ("scholarship", 5, 0), ("scholarship not received", 5, 0),
        ("admission", 3, 0), ("rte", 5, 0), ("mid day meal", 5, 0), ("midday meal", 5, 0),
        ("education", 4, 0), ("syllabus", 3, 0), ("textbook", 4, 0), ("text books", 4, 0),
        ("exam", 3, 0), ("exam hall", 3, 0), ("coaching", 2, 0), ("hostel", 3, 0),
        ("toilet in school", 3, 0), ("aanganwadi", 4, 0), ("anganwadi", 4, 0), ("educational", 3, 0),
        ("doctor", 1, 1), ("hospital", 1, 1),
    ],
    "TRANS": [
        ("bus", 4, 0), ("city bus", 4, 0), ("bus stop", 4, 0), ("bus route", 4, 0), ("conductor", 4, 0),
        ("metro", 5, 0), ("metro train", 5, 0), ("railway", 4, 0), ("train", 3, 0), ("railways", 3, 0),
        ("auto", 3, 0), ("autorickshaw", 3, 0), ("rickshaw", 3, 0), ("fare", 4, 0), ("overcharging fare", 5, 0),
        ("public transport", 5, 0), ("transport", 4, 0), ("depot", 3, 0), ("route", 3, 0),
        ("bus not running", 4, 0), ("bus cancelled", 4, 0), ("frequency", 3, 0), ("taxi", 3, 0),
        ("speed breaker", 2, 0), ("road", 1, 1), ("pothole", 1, 1),
    ],
    "ENV": [
        ("air pollution", 5, 0), ("smoke", 4, 0), ("smog", 5, 0), ("pollution", 4, 0), ("air quality", 5, 0),
        ("deforestation", 5, 0), ("tree cutting", 5, 0), ("trees cut", 5, 0), ("forest", 4, 0),
        ("noise pollution", 5, 0), ("noise", 4, 0), ("loud", 3, 0), ("dust", 3, 0), ("dust pollution", 4, 0),
        ("plastic ban", 5, 0), ("plastic", 3, 0), ("e waste", 4, 0), ("e-waste", 4, 0),
        ("industrial waste", 4, 0), ("chemical waste", 4, 0), ("river pollution", 5, 0), ("lake pollution", 5, 0),
        ("green cover", 4, 0), ("environment", 4, 0), ("biodiversity", 4, 0), ("groundwater", 3, 0),
        ("garbage", 1, 1), ("water", 1, 1), ("road", 1, 1),
    ],
    "CONSUMER": [
        ("overcharged", 5, 0), ("overcharging", 5, 0), ("cheated", 4, 0), ("defective", 5, 0), ("damaged product", 5, 0),
        ("warranty", 5, 0), ("not replaced", 4, 0), ("refund", 4, 0), ("refund not given", 5, 0),
        ("billing", 3, 0), ("false advertising", 5, 0), ("misleading", 4, 0), ("fake product", 5, 0),
        ("counterfeit", 5, 0), ("adulterated", 5, 0), ("food adulteration", 5, 0), ("mrp", 4, 0),
        ("mrp violation", 5, 0), ("shop", 3, 0), ("store", 3, 0), ("e commerce", 5, 0), ("ecommerce", 5, 0),
        ("amazon", 4, 0), ("flipkart", 4, 0), ("swiggy", 4, 0), ("zomato", 4, 0), ("restaurant", 3, 0),
        ("hotel", 2, 0), ("customer care", 3, 0), ("complaint", 2, 0), ("quality", 3, 0),
        ("electricity", 1, 1), ("phone", 1, 1),
    ],
    "AGRI": [
        ("crop", 4, 0), ("crops", 4, 0), ("farmer", 5, 0), ("farmers", 5, 0), ("farming", 4, 0),
        ("fertilizer", 5, 0), ("fertiliser", 5, 0), ("pesticide", 4, 0), ("pesticides", 4, 0),
        ("subsidy", 4, 0), ("seeds", 4, 0), ("seed", 3, 0), ("msp", 5, 0), ("crop insurance", 5, 0),
        ("irrigation", 5, 0), ("irrigation canal", 5, 0), ("canal", 4, 0), ("drip irrigation", 4, 0),
        ("agriculture", 5, 0), ("agricultural", 5, 0), ("land", 3, 0), ("farm", 3, 0),
        ("loan waiver", 4, 0), ("kisan", 5, 0), ("pm kisan", 5, 0), ("mandi", 4, 0),
        ("water", 1, 1), ("electricity", 1, 1),
    ],
    "REV": [
        ("land record", 5, 0), ("land records", 5, 0), ("land", 4, 0), ("property", 4, 0),
        ("property registration", 5, 0), ("registration", 3, 0), ("stamp duty", 5, 0), ("mutation", 5, 0),
        ("patta", 5, 0), ("patta transfer", 5, 0), ("land title", 5, 0), ("title deed", 5, 0),
        ("land dispute", 5, 0), ("encroachment", 4, 0), ("revenue office", 5, 0), ("revenue", 4, 0),
        ("village officer", 3, 0), ("tehsildar", 5, 0), ("sub registrar", 5, 0), ("sub-registrar", 5, 0),
        ("property tax", 4, 0), ("land tax", 4, 0), ("document", 3, 0), ("bhoomi", 4, 0),
        ("farmer", 1, 1), ("crop", 1, 1),
    ],
    "TELECOM": [
        ("mobile network", 5, 0), ("network", 4, 0), ("signal", 4, 0), ("poor signal", 5, 0),
        ("no signal", 5, 0), ("internet", 5, 0), ("broadband", 5, 0), ("wifi", 4, 0), ("wi-fi", 4, 0),
        ("mobile", 4, 0), ("phone", 3, 0), ("call drops", 5, 0), ("call dropping", 5, 0), ("data speed", 4, 0),
        ("network tower", 5, 0), ("tower", 4, 0), ("telecom", 5, 0), ("sim", 3, 0), ("jio", 4, 0),
        ("airtel", 4, 0), ("vi", 4, 0), ("bsnl", 4, 0), ("vodafone", 4, 0), ("4g", 4, 0), ("5g", 4, 0),
        ("electricity", 1, 1), ("land", 1, 1),
    ],
    "RATIONS": [
        ("ration card", 5, 0), ("ration", 5, 0), ("pds", 5, 0), ("public distribution", 5, 0),
        ("fair price shop", 5, 0), ("fair price", 4, 0), ("ration shop", 5, 0), ("lpg", 4, 0),
        ("gas cylinder", 4, 0), ("cooking gas", 4, 0), ("lpg connection", 4, 0), ("food grains", 4, 0),
        ("grain", 3, 0), ("rice", 3, 0), ("wheat", 3, 0), ("pulses", 3, 0), ("kerosene", 3, 0),
        ("subsidy", 3, 0), ("aadhaar linked", 4, 0), ("aadhar", 3, 0), ("epos", 4, 0),
        ("food", 3, 0), ("supply", 2, 0),
        ("electricity", 1, 1), ("school", 1, 1),
    ],
    "DM": [
        ("flood", 5, 0), ("flooding", 5, 0), ("flooded", 5, 0), ("cyclone", 5, 0), ("cyclonic", 5, 0),
        ("earthquake", 5, 0), ("landslide", 5, 0), ("landslides", 5, 0), ("relief camp", 5, 0),
        ("relief", 4, 0), ("rescue", 5, 0), ("rescued", 5, 0), ("evacuation", 5, 0), ("evacuate", 5, 0),
        ("disaster", 5, 0), ("emergency", 3, 0), ("warning", 3, 0), ("shelter", 4, 0),
        ("dam", 4, 0), ("dam breach", 5, 0), ("heavy rain", 3, 0), ("rains", 2, 0),
        ("tree", 2, 0), ("hospital", 1, 1),
    ],
}

DEMO_COMPLAINTS = [
    ("Potholes on MG Road near bus depot", "There are huge potholes on MG Road near the city bus depot. Every evening water collects there and two-wheelers are skidding. Please get them repaired urgently.",
     "Roads & Transport", "MG Road", "Pune", "411001", "Rahul Verma", "rahul.v@gmail.com", "9822000001"),
    ("Street lights not working for a week", "The street lights on the lane opposite Shanti Nagar Park have not been working for an entire week. The whole lane is dark and unsafe at night. Students returning from tuitions are scared.",
     "Street Lights", "Shanti Nagar", "Lucknow", "226001", "Anita Singh", "anita.singh@yahoo.in", "9839000002"),
    ("Garbage not collected for 10 days", "Garbage has not been collected from our colony for the past ten days. The dustbins are overflowing and there are flies and bad smell everywhere. This is a health hazard for children.",
     "Sanitation", "Green Park Colony", "Jaipur", "302001", "Mohd. Faiz", "faiz.m@gmail.com", "9414000003"),
    ("Frequent power cuts during peak hours", "We are facing frequent power cuts and low voltage between 6 pm and 10 pm every day in our residential society. Household appliances are getting damaged and inverters are not helping.",
     "Electricity", "Sunrise Apartments", "Surat", "395007", "Kiran Patel", "kiran.patel@gmail.com", "9428000004"),
    ("Water pipeline burst on main road", "A water pipeline has burst on the main road near the old vegetable market. Clean drinking water is being wasted and the road is flooded. The water supply to nearby houses has stopped.",
     "Water Supply", "Old Market Road", "Nagpur", "440001", "Suresh Yadav", "suresh.y@gmail.com", "9860000005"),
    ("Water tanker not reaching our area", "Our area has not received water from the municipal tanker for the last five days. Summer heat is unbearable and there is no water for drinking or bathing.",
     "Water Supply", "Basanti Colony", "Gwalior", "474001", "Rekha Sharma", "rekha.sh@gmail.com", "9300000006"),
    ("Mobile network and internet issues", "For the past month, mobile network and internet data speeds have been extremely poor in our locality. Calls keep dropping and videos do not load even at night. Our area has only one weak network tower.",
     "Telecom", "Model Town", "Ludhiana", "141001", "Gurpreet Singh", "gurpreet.s@gmail.com", "9872000007"),
    ("Theft in our neighbourhood", "There have been three chain snatching incidents in our lane within two weeks. The police patrolling is very weak and residents are scared to go out after dark.",
     "Police & Safety", "Hazratganj", "Lucknow", "226001", "Priya Gupta", "priya.g@gmail.com", "9415000008"),
    ("Government hospital hygiene and staff", "The district government hospital has very poor hygiene and the nursing staff are rude to patients. Sanitation in the wards is neglected and medicines are out of stock in the pharmacy.",
     "Health", "Civil Lines", "Kanpur", "208001", "Deepak Kumar", "deepak.k@gmail.com", "9415000009"),
    ("No bus on our route for months", "The city bus service on route 42 from our village to the district bus stand has been suspended for three months. Students and daily wage workers are badly affected as there is no alternative transport.",
     "Public Transport", "Village Bhogpur", "Varanasi", "221001", "Vijay Pal", "vijay.p@gmail.com", "9621000010"),
    ("Ration card not linked to Aadhaar", "My ration card is not linked to Aadhaar, and the fair price shop dealer is refusing to give my family our monthly food grains. We have been visiting the PDS office for three weeks with no resolution.",
     "Food Supplies", "Raja Bazar", "Patna", "800001", "Manoj Kumar", "manoj.k@gmail.com", "9931000011"),
    ("Crop insurance claim rejected", "The crop insurance for my paddy crop was rejected citing a technical issue, even though the flood destroyed my entire field. I am a small farmer and this claim is my only hope this season.",
     "Agriculture", "Village Rampur", "Meerut", "250001", "Ram Singh", "ram.s@gmail.com", "9456000012"),
    ("Air pollution from nearby factory", "A chemical factory near our residential area releases thick smoke through the night. Air quality is terrible and children are getting breathing problems. Please inspect and act immediately.",
     "Environment", "Phase II Industrial Area", "Faridabad", "121001", "Neha Gupta", "neha.g@gmail.com", "9818000013"),
    ("Land mutation pending for months", "The land mutation of my inherited property has been pending at the tehsildar office for six months. My brother has started a dispute and I need the mutation done urgently for bank loan approval.",
     "Revenue & Land", "Tehsil Office", "Ambala", "133001", "Harpreet Kaur", "harpreet.k@gmail.com", "9872000014"),
    ("Overcharging at a shop without bill", "A local mobile shop sold me a phone for 2000 rupees above the MRP and refused to give a proper bill or warranty card. When I complained to the shop, they threatened me.",
     "Consumer Rights", "Sadar Bazar", "Bhopal", "462001", "Arjun Meena", "arjun.m@gmail.com", "9425000015"),
    ("School lacks basic facilities", "The government school in our village has no drinking water facility and the girls' toilet is locked and broken. Children have to go home for water and attendance is dropping.",
     "Education", "Village Chandpur", "Aligarh", "202001", "Shabana Khan", "shabana.k@gmail.com", "9897000016"),
    ("Dengue outbreak in our area", "There are many dengue and malaria cases in our area this monsoon. Mosquito breeding is everywhere due to open drains and construction water logging. We need an urgent fogging and health camp.",
     "Health", "Rajiv Nagar", "Bhopal", "462001", "Sunita Devi", "sunita.d@gmail.com", "9407000017"),
    ("Railway foot over bridge unsafe", "The foot over bridge at our railway station is in a crumbling condition with broken steps and no lighting at night. Old people and children are at high risk of falling.",
     "Railways", "Railway Station", "Saharanpur", "247001", "Nitin Garg", "nitin.g@gmail.com", "9412000018"),
    ("Loudspeaker noise after permitted hours", "A shop in our area plays loudspeakers at full volume after 10 pm every night in violation of noise pollution rules. Elderly residents and students cannot sleep.",
     "Noise Pollution", "Clock Tower", "Moradabad", "244001", "Poonam Rani", "poonam.r@gmail.com", "9837000019"),
    ("Flood relief not reaching village", "Our village is still flooded after the dam water release and relief material has not reached us. We need boats and rescue for the families stranded on the rooftops.",
     "Disaster Relief", "Village Sarai", "Darbhanga", "846004", "Ravi Kumar", "ravi.k@gmail.com", "9431000020"),
]

DEFAULT_DEPT_CODES = {
    "MCD": "MCD", "PWD": "PWD", "EB": "EB", "WS": "WS", "POLICE": "POLICE",
    "HEALTH": "HEALTH", "EDU": "EDU", "TRANS": "TRANS", "ENV": "ENV",
    "CONSUMER": "CONSUMER", "AGRI": "AGRI", "REV": "REV", "TELECOM": "TELECOM",
    "RATIONS": "RATIONS", "DM": "DM",
}


def _dep_id(conn, code: str) -> int:
    row = conn.execute("SELECT id FROM departments WHERE code = ?", (code,)).fetchone()
    return row["id"] if row else None


def seed(force: bool = False) -> None:
    init_db()
    with db() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM departments").fetchone()["c"]
        if count > 0 and not force:
            return

        for d in DEPARTMENTS:
            conn.execute(
                "INSERT INTO departments(code,name,description,contact_email,contact_phone,color) "
                "VALUES (?,?,?,?,?,?)",
                (d["code"], d["name"], d["description"], d["contact_email"],
                 d["contact_phone"], d["color"]),
            )

        for code, kws in KEYWORDS.items():
            did = _dep_id(conn, code)
            for kw, weight, neg in kws:
                conn.execute(
                    "INSERT INTO keywords(department_id, keyword, weight, is_negative) VALUES (?,?,?,?)",
                    (did, kw, weight, neg),
                )


def seed_demo_complaints() -> None:
    """Insert demo complaints routed through the real engine (if table empty)."""
    from ..routing.service import router

    with db() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM complaints").fetchone()["c"]
        if count > 0:
            return

    with db() as conn:
        ucount = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
    if ucount == 0:
        _seed_demo_users()

    for (title, desc, cat, loc, city, pin, name, email, phone) in DEMO_COMPLAINTS:
        result = router.analyze(title, desc)
        dept_id = result["department_id"]
        if dept_id is None:
            dept_id = _resolve_default(title, desc)
        _insert_complaint(
            title, desc, cat, loc, city, pin, name, email, phone,
            dept_id, result, note="Seeded demo complaint",
        )

    _seed_demo_feedback()


def _seed_demo_users() -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO users(full_name, email, phone, city, role, created_at) VALUES "
            "('Ananya Iyer','ananya@example.com','9811100001','Pune','citizen',?),"
            "('Mohd. Faiz','faiz@example.com','9811100002','Jaipur','citizen',?),"
            "('Gurpreet Singh','gurpreet@example.com','9811100003','Ludhiana','citizen',?)",
            (now_utc(), now_utc(), now_utc()),
        )


def _seed_demo_feedback() -> None:
    with db() as conn:
        fcount = conn.execute("SELECT COUNT(*) AS c FROM feedback").fetchone()["c"]
        if fcount > 0:
            return
        rows = conn.execute("SELECT id FROM complaints LIMIT 8").fetchall()
        users = conn.execute("SELECT id FROM users LIMIT 3").fetchall()
        comments = [
            (5, "Very responsive team, issue resolved quickly!"),
            (4, "Good work, but took a little longer than expected."),
            (3, "Status updates were helpful but action was slow."),
            (2, "Still waiting for the problem to be fixed."),
            (5, "Excellent! The department contacted me the same day."),
            (4, "Happy with the follow-up on my complaint."),
        ]
        for i, row in enumerate(rows):
            rating, comment = comments[i % len(comments)]
            user = users[i % len(users)] if users else None
            conn.execute(
                "INSERT INTO feedback(complaint_id, user_id, rating, comment, channel, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (row["id"], user["id"] if user else None, rating, comment, "web", now_utc()),
            )


def _resolve_default(title: str, desc: str) -> int | None:
    text = f"{title} {desc}".lower()
    for code, hint in [("MCD", ["street light", "garbage"]), ("WS", ["water"]),
                       ("POLICE", ["chain snatching", "theft"]),
                       ("EB", ["power"]), ("RATIONS", ["ration"]),
                       ("TRANS", ["bus"]), ("ENV", ["pollution"]),
                       ("AGRI", ["crop"]), ("REV", ["mutation"]),
                       ("CONSUMER", ["mrp"]), ("EDU", ["school"]),
                       ("HEALTH", ["dengue", "hospital"]), ("DM", ["flood"]),
                       ("TELECOM", ["network"]), ("PWD", ["road"])]:
        if any(h in text for h in hint):
            with db() as conn:
                row = conn.execute("SELECT id FROM departments WHERE code = ?", (code,)).fetchone()
            if row:
                return row["id"]
    return None


def _insert_complaint(title, desc, cat, loc, city, pin, name, email, phone,
                      dept_id, result, note="") -> str:
    from .complaint import create_complaint
    return create_complaint(
        title=title, description=desc, category=cat, location=loc, city=city,
        pincode=pin, contact_name=name, contact_email=email, contact_phone=phone,
        department_id=dept_id, confidence=result["confidence"],
        method=result["method"], matched_keywords=result["matched_keywords"],
        note=note, status="PENDING",
    )
