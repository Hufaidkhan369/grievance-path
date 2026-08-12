import logging
from app.routing.service import router
from app.database import init_db
from app.services.seed import seed

logging.basicConfig(level=logging.WARNING)
init_db()
seed()

tests = [
    ("Garbage not collected for 10 days in our colony", "The dustbins are overflowing and there is bad smell everywhere"),
    ("Frequent power cuts and low voltage every evening", "Our appliances are getting damaged"),
    ("Water pipeline burst on main road", "Clean water wasted, supply stopped"),
    ("Chain snatching incidents in our lane", "Residents scared to go out after dark"),
    ("Bus service suspended on route 42", "Students badly affected"),
    ("Crop insurance rejected after floods", "Farmer needs help"),
    ("Mobile network tower weak, internet slow", "Calls keep dropping"),
    ("Defective mobile phone sold above MRP", "Shop refused warranty and a bill"),
    ("Ration card not linked to Aadhaar", "Fair price shop refused food grains"),
    ("Street lights not working", "Lane is dark and unsafe at night"),
]
ok = 0
for title, desc in tests:
    r = router.analyze(title, desc)
    flag = "OK" if r["department_id"] else "??"
    if r["department_id"]:
        ok += 1
    print(f"[{flag}] {r['department_name']:26s} conf={r['confidence']:.2f} method={r['method']:12s}")
print(f"\n{ok}/{len(tests)} routed")
