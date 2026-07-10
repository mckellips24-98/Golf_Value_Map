#!/usr/bin/env python3
"""
Golf Value Map - data builder
=============================
This script generates data/courses.json from the structured lists below.

Sources (pulled July 2026):
  - Minnesota Golf Card: https://minnesotagolfcard.com  (courses.php, courses-alpha.php, ride-a-round.php)
  - Public Country Club: https://www.thepubliccc.com/courses and /faq

HOW TO UPDATE EACH SEASON (no coding required beyond editing lists):
  1. Edit the MGC_COURSES, PCC_ONLY, and OVERLAP tables below to match the new season.
  2. Run:  python3 build_data.py
  3. Commit the regenerated data/courses.json

If you prefer, you can also edit data/courses.json directly by hand -
the app only reads the JSON file, never this script.

NOTE ON COORDINATES: lat/lng values are CITY-LEVEL approximations so every
course shows on the map immediately. For pin-perfect accuracy, look up the
course on Google Maps, right-click the clubhouse, copy the coordinates, and
paste them into data/courses.json (set "coordSource": "exact").
"""

import json, re, unicodedata

# ---------------------------------------------------------------------------
# Minnesota Golf Card time levels (from courses.php)
# ---------------------------------------------------------------------------
MGC_LEVELS = {
    "A": "Valid anytime. Holidays and July 3-5 not included.",
    "B": "Valid anytime Mon-Fri; Sat & Sun after 1 pm. Holidays and July 3-5 not included.",
    "C": "Valid anytime Mon-Thu; Fri, Sat & Sun after 3 pm. Holidays and July 3-5 not included.",
    "D": "Valid Mon-Thu, only on/before May 31 and on/after Sept 1. Holidays not included.",
    "E": "Valid Mon-Thu before 11 am; Sat & Sun after 1 pm. Holidays and July 3-5 not included.",
    "F": "Valid Mon-Fri after 12 pm; Sat & Sun after 2 pm. Holidays and July 3-5 not included.",
    "G": "Discounted-rate course (not 2-for-1). Valid Mon-Thu. 4 rounds, up to 2 redeemed per visit; coupon = 1 round + half a power cart.",
}

MGC_CART_LEGEND = {
    "1": "No golf cart discount",
    "2": "No driving range discount",
    "3": "Cart included in green fee",
    "4": "Driving range included in green fee",
    "5": "9-hole course",
    "6": "Power cart required",
}

PCC_TIERS = {
    "1": "Tier 1: No green-fee surcharge. Cart $23/18 or $15/9 if riding. Weekend/holiday blackout 7-11 am (cart required before 7 am wknd/holiday). Max 12 rounds/month/course. Shoulder-season surcharge Nov-Mar.",
    "2": "Tier 2: Mon-Thu cart $23/18, $15/9, or $10 walking surcharge. Fri-Sun & holidays $28 mandatory surcharge (cart included). Weekend/holiday blackout 7 am-12 pm. Max 12 rounds/month/course.",
    "3": "Tier 3: $33 surcharge every day (cart included if taken). Weekend/holiday blackout 7 am-12 pm. Max 12 rounds/month/course.",
    "RESORT": "Resort tier: $45 surcharge, limited to 6 rounds/month. Weekend/holiday blackout 7 am-12 pm.",
}

# ---------------------------------------------------------------------------
# City-level coordinates (approximate). Format: "City|ST": (lat, lng)
# ---------------------------------------------------------------------------
CITY_COORDS = {
    "Alexandria|MN": (45.885, -95.377), "Benson|MN": (45.315, -95.600),
    "Blackduck|MN": (47.734, -94.548), "New Brighton|MN": (45.066, -93.202),
    "Coon Rapids|MN": (45.173, -93.303), "Brooklyn Center|MN": (45.076, -93.333),
    "St Paul|MN": (44.944, -93.093), "Fort Snelling|MN": (44.892, -93.181),
    "Glencoe|MN": (44.769, -94.152), "Ada|MN": (47.300, -96.515),
    "Atwater|MN": (45.139, -94.778), "Lake City|MN": (44.450, -92.268),
    "Litchfield|MN": (45.127, -94.528), "Melrose|MN": (45.674, -94.807),
    "North Branch|MN": (45.511, -92.980), "Pine City|MN": (45.826, -92.969),
    "Plainview|MN": (44.165, -92.171), "Janesville|MN": (44.116, -93.708),
    "Red Wing|MN": (44.566, -92.534), "Redwood Falls|MN": (44.539, -95.117),
    "Anoka|MN": (45.198, -93.387), "Annandale|MN": (45.263, -94.124),
    "Walker|MN": (47.101, -94.587), "Wadena|MN": (46.442, -95.136),
    "Sartell|MN": (45.621, -94.207), "Wahpeton|ND": (46.265, -96.606),
    "Somerset|WI": (45.124, -92.672), "Rush City|MN": (45.685, -92.965),
    "Cannon Falls|MN": (44.507, -92.906), "Lino Lakes|MN": (45.160, -93.089),
    "River Falls|WI": (44.861, -92.624), "New Prague|MN": (44.543, -93.576),
    "Deerwood|MN": (46.474, -93.899), "Elk River|MN": (45.304, -93.567),
    "Hastings|MN": (44.743, -92.852), "Emily|MN": (46.731, -93.958),
    "Stacy|MN": (45.398, -92.987), "Cedar|MN": (45.338, -93.247),
    "Kimball|MN": (45.313, -94.300), "Faribault|MN": (44.295, -93.269),
    "Ramsey|MN": (45.261, -93.450), "White Bear Lake|MN": (45.085, -93.010),
    "Frazee|MN": (46.728, -95.700), "Marshall|MN": (44.447, -95.788),
    "Sturgeon Lake|MN": (46.381, -92.826), "Stillwater|MN": (45.056, -92.806),
    "Baudette|MN": (48.712, -94.600), "Cambridge|MN": (45.573, -93.224),
    "Cold Spring|MN": (45.456, -94.429), "Mora|MN": (45.877, -93.294),
    "Spring Valley|WI": (44.844, -92.239), "Oak Grove|MN": (45.341, -93.327),
    "Staples|MN": (46.355, -94.792), "Moorhead|MN": (46.874, -96.768),
    "Virginia|MN": (47.523, -92.537), "Waseca|MN": (44.078, -93.507),
    "Rochester|MN": (44.022, -92.470), "Albany|MN": (45.630, -94.570),
    "Brooklyn Park|MN": (45.094, -93.356), "Detroit Lakes|MN": (46.817, -95.845),
    "Minneapolis|MN": (44.977, -93.265), "Onamia|MN": (46.070, -93.667),
    "Spicer|MN": (45.233, -94.940), "Long Prairie|MN": (45.975, -94.866),
    "Mahnomen|MN": (47.315, -95.968), "Monticello|MN": (45.306, -93.794),
    "Frontenac|MN": (44.512, -92.359), "Rice Lake|WI": (45.506, -91.738),
    "Houston|MN": (43.763, -91.569), "Menahga|MN": (46.754, -95.098),
    "Chanhassen|MN": (44.862, -93.531), "Elko|MN": (44.565, -93.327),
    "Albertville|MN": (45.238, -93.654), "Nisswa|MN": (46.520, -94.288),
    "Paynesville|MN": (45.380, -94.712), "Ham Lake|MN": (45.250, -93.250),
    "New Richmond|WI": (45.123, -92.536), "Golden Valley|MN": (44.985, -93.377),
    "Willmar|MN": (45.122, -95.043), "Coleraine|MN": (47.288, -93.427),
    "Milaca|MN": (45.756, -93.654), "Maple Grove|MN": (45.072, -93.456),
    "Bemidji|MN": (47.474, -94.880), "Owatonna|MN": (44.084, -93.226),
    "Lindstrom|MN": (45.389, -92.848), "Prescott|WI": (44.749, -92.802),
    "Roseville|MN": (45.006, -93.156), "St Peter|MN": (44.324, -93.958),
    "Lutsen|MN": (47.647, -90.673), "Forest Lake|MN": (45.279, -92.985),
    "Pequot Lakes|MN": (46.603, -94.309), "Brainerd|MN": (46.358, -94.200),
    "Hudson|WI": (44.975, -92.757),
    # PCC-only cities
    "Afton|MN": (44.903, -92.783), "Winona|MN": (44.050, -91.639),
    "Webster City|IA": (42.469, -93.816), "Buffalo|MN": (45.172, -93.875),
    "Crosslake|MN": (46.684, -94.113), "Hutchinson|MN": (44.888, -94.370),
    "Lakeville|MN": (44.649, -93.243), "Dayton|MN": (45.244, -93.510),
    "Dodge Center|MN": (44.028, -92.855), "Holmen|WI": (43.963, -91.256),
    "Woodbury|MN": (44.924, -92.959), "Duluth|MN": (46.787, -92.100),
    "Farmington|MN": (44.640, -93.143), "Webster|WI": (45.877, -92.363),
    "Hayward|WI": (46.013, -91.485), "Park Rapids|MN": (46.922, -95.058),
    "Solon Springs|WI": (46.351, -91.815), "Shoreview|MN": (45.079, -93.147),
    "Two Harbors|MN": (47.022, -91.671), "Austin|MN": (43.667, -92.975),
    "McGregor|MN": (46.607, -93.313), "Montgomery|MN": (44.439, -93.581),
    "Superior|WI": (46.720, -92.104), "New Hope|MN": (45.038, -93.386),
    "Garrison|MN": (46.294, -93.827), "Buffalo Lake|MN": (44.737, -94.617),
    "Becker|MN": (45.393, -93.877), "Fergus Falls|MN": (46.283, -96.078),
    "Pine Island|MN": (44.201, -92.646), "Grand Rapids|MN": (47.237, -93.530),
    "Maplewood|MN": (44.953, -93.025), "Cottage Grove|MN": (44.828, -92.944),
    "Lake Elmo|MN": (44.996, -92.879), "Lester Prairie|MN": (44.884, -94.042),
    "Corcoran|MN": (45.095, -93.548), "Silver Bay|MN": (47.294, -91.257),
    "Siren|WI": (45.786, -92.381), "St James|MN": (43.982, -94.627),
    "Spooner|WI": (45.822, -91.889), "Shakopee|MN": (44.798, -93.527),
    "Cohasset|MN": (47.263, -93.620), "St Cloud|MN": (45.560, -94.162),
    "St Francis|MN": (45.387, -93.359), "International Falls|MN": (48.601, -93.404),
    "Ottertail|MN": (46.425, -95.556), "Watertown|MN": (44.963, -93.847),
    "Elbow Lake|MN": (45.994, -95.977), "Trempealeau|WI": (44.006, -91.442),
    "Apple Valley|MN": (44.732, -93.218), "Otsego|MN": (45.284, -93.612),
    "Danbury|WI": (46.010, -92.376), "Northfield|MN": (44.458, -93.162),
    "Zumbrota|MN": (44.294, -92.669), "Zumbro Falls|MN": (44.284, -92.422),
    "Sauk Centre|MN": (45.737, -94.952), "Hopkins|MN": (44.925, -93.417),
    "Pella|IA": (41.408, -92.916),
}

# ---------------------------------------------------------------------------
# Minnesota Golf Card courses (2026 season)
# (name, city, state, phone, level, cart_codes, par, website, address, ride_a_round)
# For Level G courses, website field may be "" and address includes rates in notes.
# ---------------------------------------------------------------------------
MGC_COURSES = [
    # ----- Level A -----
    ("Atikwa Golf Club at Arrowwood Resort","Alexandria","MN","320-762-8337","A","6","72","https://www.arrowwoodresort.com","2100 Arrowwood Ln NW, Alexandria, MN 56308",True),
    ("Benson Golf Club","Benson","MN","320-842-7901","A","1,2,6","72","https://www.bensongolfclub.com","2222 Atlantic Ave, Benson, MN 56215",False),
    ("Blackduck Golf Course","Blackduck","MN","218-835-7757","A","1,2,6","36","https://www.blackduckmn.com","20857 Blackduck Lake Rd NE, Blackduck, MN 56630",False),
    ("Brightwood Hills Golf Course","New Brighton","MN","651-638-2150","A","1,5","30","https://www.newbrightonmn.gov","1975 Silver Lake Rd, New Brighton, MN 55112",True),
    ("Bunker Hills Golf Club - Exec 9","Coon Rapids","MN","763-755-4141","A","1,2","31","https://www.bunkerhillsgolf.com","12800 Bunker Prairie Rd, Coon Rapids, MN 55448",False),
    ("Centerbrook Golf Course","Brooklyn Center","MN","763-549-3750","A","2,5","27","https://www.centerbrookgolf.com","5500 N Lilac Dr, Brooklyn Center, MN 55430",True),
    ("Fort Snelling Golf Course","Fort Snelling","MN","612-726-6222","A","1,2,5,6","35","https://www.minneapolisparks.org","6399 Fort Snelling Ave, Bldg 175, St Paul, MN 55111",True),
    ("Glencoe Country Club","Glencoe","MN","320-864-3023","A","2,6","71","https://www.glencoecountryclub.net","1325 E 1st St, Glencoe, MN 55336",True),
    ("Heart of the Valley Golf Course","Ada","MN","218-784-4746","A","1,2,6","36","https://www.hovgolf.com","1949 Co Hwy 35, Ada, MN 56510",True),
    ("Island Pine Golf Club","Atwater","MN","320-974-8600","A","1,2,6","72","https://www.islandpinegolf.com","1601 Wyoming Ave W, Atwater, MN 56209",True),
    ("Lake City Golf Club","Lake City","MN","651-345-3221","A","1,2,6","71","https://www.lakecitygolf.com","33587 Lakeview Dr, Lake City, MN 55041",False),
    ("Litchfield Golf Club","Litchfield","MN","320-693-6059","A","1,2","70","https://www.litchfieldgolfclub.com","126 N Marshall Ave, Litchfield, MN 55355",False),
    ("Meadowlark Country Club","Melrose","MN","320-256-4989","A","1,2,6","36","https://www.meadowlarkcountryclub.com","837 Country Club Dr, Melrose, MN 56352",True),
    ("North Branch Golf Course","North Branch","MN","651-674-9989","A","1,2,5,6","35","https://www.nbgolfcourse.com","38585 Forest Blvd, North Branch, MN 55056",False),
    ("Pine City Country Club","Pine City","MN","320-629-3848","A","1,5","36","https://www.pinecitycountryclub.com","10413 Golf Course Rd SW, Pine City, MN 55063",True),
    ("Piper Hills Golf Course","Plainview","MN","507-534-2613","A","1,2,5,6","36","","Plainview, MN 55964",True),
    ("Prairie Ridge Golf Course","Janesville","MN","507-234-5505","A","1,2,5,6","36","https://www.prairieridgegolf.com","2000 N Main St, Janesville, MN 56048",False),
    ("Red Wing Golf Club","Red Wing","MN","651-388-9524","A","1,2,6","71","https://www.redwinggolfclub.com","1311 W 6th St, Red Wing, MN 55066",False),
    ("Redwood Falls Golf Club","Redwood Falls","MN","507-627-8901","A","1,2,6","70","https://www.redwoodfallsgolf.com","101 E Oak St, Redwood Falls, MN 56283",False),
    ("Rum River Hills Golf Club","Anoka","MN","763-753-3339","A","","71","https://www.rumriverhills.com","16659 St Francis Blvd, Anoka, MN 55303",True),
    ("Southbrook Golf Club","Annandale","MN","320-274-2341","A","1,2","72","https://www.southbrookgolf.com","511 Morrison Ave S, Annandale, MN 55302",False),
    ("Tianna Country Club","Walker","MN","218-547-1712","A","6","72","https://www.tianna.com","7470 State Hwy 34 NW, Walker, MN 56484",False),
    ("Whitetail Run Golf Course","Wadena","MN","218-631-7718","A","2,6","72","https://www.whitetailrungolfcourse.com","13379 Leaf River Rd, Wadena, MN 56482",True),
    # ----- Level B -----
    ("Blackberry Ridge Golf Club","Sartell","MN","320-257-4653","B","","72","https://www.blackberryridgegolf.com","Sartell, MN 56377",False),
    ("Bois De Sioux Golf Club","Wahpeton","ND","701-642-3673","B","1","72","","1305 RJ Hughes Dr, Wahpeton, ND 58075",False),
    ("Bristol Ridge Golf Course","Somerset","WI","715-247-3673","B","6","72","https://www.bristolridgegolfcourse.com","Somerset, WI 54025",True),
    ("Bulrush Golf Club","Rush City","MN","320-358-1050","B","6","72","https://www.bulrushgolfclub.com","605 Brookside Pkwy, Rush City, MN 55069",True),
    ("Cannon Golf Club","Cannon Falls","MN","507-263-3126","B","1,2,6","71","https://www.cannongolfclub.com","8606 295th St E, Cannon Falls, MN 55309",False),
    ("Chomonix Golf Course","Lino Lakes","MN","651-482-8484","B","1,6","72","https://www.chomonix.com","700 Aqua Ln, Lino Lakes, MN 55014",False),
    ("Clifton Hollow Golf Course","River Falls","WI","715-425-9781","B","1,2,6","71","https://www.cliftonhollow.com","W12166 820th Ave, River Falls, WI 54022",False),
    ("Creeks Bend Golf Course","New Prague","MN","952-758-7200","B","6","72","https://www.creeksbendgolfcourse.com","26826 Langford Ave, New Prague, MN 56071",True),
    ("Cuyuna Rolling Hills","Deerwood","MN","218-534-3489","B","1,2,6","72","https://www.cuyunarollinghillsgolf.com","24410 State Hwy 210, Deerwood, MN 56444",False),
    ("Elk River Golf Club","Elk River","MN","763-441-4111","B","1","72","https://www.elkrivercc.com","20015 Elk Lake Rd, Elk River, MN 55330",False),
    ("Emerald Greens Golf Course","Hastings","MN","651-480-8558","B","1,2,6","72","https://www.emeraldgreensgolf.com","14425 Goodwin Ave, Hastings, MN 55033",False),
    ("Emily Greens Golf Course","Emily","MN","218-763-2169","B","","69","https://www.emilygreens.com","39966 Refuge Rd, Emily, MN 56447",False),
    ("Falcon Ridge Golf Course","Stacy","MN","651-462-5797","B","1,2,6","71","https://www.falconridgegolf.net","33942 Falcon Ave, Stacy, MN 55079",False),
    ("Gopher Hills Golf Course","Cannon Falls","MN","888-487-6634","B","1,6","72","https://www.gopherhills.com","26155 Nicolai Ave, Cannon Falls, MN 55009",False),
    ("Hidden Greens Golf Course","Hastings","MN","651-437-3085","B","1,2,6","72","https://www.hiddengreensgolf.com","12977 200th St E, Hastings, MN 55033",False),
    ("Hidden Haven Golf Club","Cedar","MN","763-434-6867","B","1,2,6","71","https://www.hiddenhavengolfclub.com","20520 Polk St, Cedar, MN 55011",False),
    ("Kimball Golf Course","Kimball","MN","320-398-2285","B","1,2","72","https://www.kimballgolf.com","11823 Cty Rd 150, Kimball, MN 55353",False),
    ("Legacy Golf Course","Faribault","MN","507-332-7177","B","1,2","72","https://www.legacygolf.net","1515 Shumway Ave, Faribault, MN 55021",False),
    ("Links at Northfork","Ramsey","MN","763-241-0506","B","1,6","72","https://www.golfthelinks.com","9333 Alpine Dr NW, Ramsey, MN 55303",False),
    ("Manitou Ridge Golf Course","White Bear Lake","MN","651-777-2987","B","1,2,6","71","https://www.manitouridge.com","3200 McKnight Rd, White Bear Lake, MN 55110",False),
    ("Maple Hills Golf Club","Frazee","MN","218-847-9532","B","2,5","36","https://www.maplehillsgolfclub.com","12561 Maple Hills Dr, Frazee, MN 56544",False),
    ("Marshall Golf Club","Marshall","MN","507-537-1622","B","1,2,6","72","https://www.marshallgolfclub.com","Marshall, MN 56258",False),
    ("Moose Lake Golf Club","Sturgeon Lake","MN","218-485-4886","B","1,2,5","34","","35311 Parkview Dr, Sturgeon Lake, MN 55783",False),
    ("Oak Glen Golf Course","Stillwater","MN","651-439-6981","B","1,2,6","72","https://www.oakglengolf.com","1599 McKusick Rd, Stillwater, MN 55082",False),
    ("Oak Harbor Golf Club","Baudette","MN","218-634-9939","B","1,2,6","72","https://www.oakharborgolfcourse.com","2805 24th St NW, Baudette, MN 56623",False),
    ("Oneka Ridge Golf Club","White Bear Lake","MN","651-429-2390","B","6","72","https://www.onekaridgegc.com","5610 120th St N, White Bear Lake, MN 55110",False),
    ("Purple Hawk Golf Course","Cambridge","MN","763-689-3800","B","1,2,6","72","https://www.purplehawk.com","Cambridge, MN 55008",True),
    ("Rich Spring Golf Club","Cold Spring","MN","320-685-8810","B","1,2,6","72","https://www.richspringgolf.com","17467 Fairway Cir, Cold Spring, MN 56320",True),
    ("River Oaks Golf Course - Cold Spring","Cold Spring","MN","320-685-4138","B","1,2","70","https://www.riveroaksgc.com","23742 Co Rd 2, Cold Spring, MN 56320",True),
    ("Spring Brook Golf Club","Mora","MN","320-679-2317","B","1","70","https://www.springbrookgc.com","Mora, MN 55051",True),
    ("Spring Valley Golf Course","Spring Valley","WI","715-778-5513","B","1,2","72","https://www.springvalleygolf.net","345 Hidden Fox Ct, Spring Valley, WI 54767",False),
    ("The Ponds Golf Course","St Francis","MN","763-753-1100","B","1,2,6","72","https://www.thepondsgolf.com","21250 Yellow Pine St, Oak Grove, MN 55011",False),
    ("The Refuge Golf Club","Oak Grove","MN","763-753-8383","B","1,2,6","72","https://www.refugegolfclub.com","21250 Yellow Pine St, Oak Grove, MN 55011",False),
    ("The Summit Golf Club","Cannon Falls","MN","877-582-4653","B","1,2,6","72","https://www.summitgolfclub.com","31286 Highway 19 Blvd, Cannon Falls, MN 55009",False),
    ("The Vintage Golf Club","Staples","MN","218-894-9907","B","1,6","72","https://www.vintagegolfclub.com","27923 McGivern Dr, Staples, MN 56479",False),
    ("Village Green Golf Course","Moorhead","MN","218-299-7888","B","1,2","72","https://www.moorheadgolf.com","3420 Village Green Blvd, Moorhead, MN 56560",False),
    ("Virginia Golf Course","Virginia","MN","218-748-7530","B","2","71","https://www.virginiamngolf.com","1308 18th St N, Virginia, MN 55792",False),
    ("Waseca Lakeside Club","Waseca","MN","507-835-2574","B","1,2,6","71","https://www.wasecagolf.com","37160 Clear Lake Dr, Waseca, MN 56093",False),
    ("Whispering Pines Golf Course","Annandale","MN","320-274-8721","B","1,2,6","72","https://www.whisperingpinesgolf.com","8713 70th St NW, Annandale, MN 55302",True),
    ("Willow Creek Golf Course","Rochester","MN","507-285-0305","B","1,6","70","https://www.wpgolf.com","1700 48th St SW, Rochester, MN 55902",True),
    # ----- Level C -----
    ("Albany Golf Club","Albany","MN","320-845-2505","C","1,2,6","72","https://www.albanygolfcourse.com","330 Church Ave, Albany, MN 56307",False),
    ("Bellwood Oaks Golf Course","Hastings","MN","651-437-4141","C","1,2,6","73","https://www.bellwoodoaksgolf.com","13239 210th St, Hastings, MN 55033",False),
    ("Brookland Golf Park","Brooklyn Park","MN","763-488-6497","C","2","30","https://www.brooklynpark.org","5600 85th Ave N, Brooklyn Park, MN 55443",False),
    ("Detroit Country Club","Detroit Lakes","MN","218-847-5790","C","1,2,6","64","https://www.detroitcountryclub.com","1502 Lynn Ave, Detroit Lakes, MN 56501",False),
    ("Hiawatha Golf Course","Minneapolis","MN","612-230-6525","C","1,2,6","73","https://www.minneapolisparks.org","4553 Longfellow Ave, Minneapolis, MN 55407",False),
    ("Izatys Golf Course - Black Brook","Onamia","MN","320-532-4574","C","1,3","72","https://www.izatys.com","40005 85th Ave, Onamia, MN 56359",False),
    ("Little Crow Country Club","Spicer","MN","320-354-2296","C","1,2,6","72","https://www.littlecrowgolf.com","Spicer, MN 56288",False),
    ("Long Prairie Country Club","Long Prairie","MN","320-732-3312","C","1,2,6","72","https://www.longprairiecountryclub.com","406 6th St SE, Long Prairie, MN 56347",False),
    ("Mahnomen Country Club","Mahnomen","MN","218-935-5188","C","6","36","https://mahnomencountryclub.co","2267 155th Ave, Mahnomen, MN 56557",False),
    ("Monticello Country Club","Monticello","MN","763-295-4653","C","1,2,6","71","https://www.montigolf.com","Monticello, MN 55362",False),
    ("Mount Frontenac Golf Course","Frontenac","MN","800-488-5826","C","1","71","https://www.mountfrontenac.com","32420 Ski Rd, Frontenac, MN 55026",True),
    ("New Prague Golf Club","New Prague","MN","952-758-5326","C","1,2,6","72","https://www.newpraguegolf.com","400 Lexington Ave S, New Prague, MN 56071",False),
    ("Turtleback Golf Course","Rice Lake","WI","715-234-7641","C","1,2,6","71","https://www.turtlebackgolf.com","1985 18 1/2 St, Rice Lake, WI 54868",False),
    ("Valley High Golf Club","Houston","MN","507-894-4444","C","1,2,6","71","https://www.valleyhighgolfclub.com","9203 Mound Prairie Dr, Houston, MN 55943",False),
    # ----- Level D -----
    ("Blueberry Pines Golf Club","Menahga","MN","218-564-4653","D","1,2,6","72","https://www.blueberrypinesgolf.com","39161 US Hwy 71, Menahga, MN 56464",False),
    ("Bluff Creek Golf Course","Chanhassen","MN","952-445-5685","D","1,2,6","72","https://www.bluffcreek.com","Chanhassen, MN 55317",False),
    ("Boulder Pointe Golf Club","Elko","MN","952-461-4900","D","1,2,6","71","https://www.boulderpointegolf.com","9575 Glenborough Dr, Elko, MN 55020",False),
    ("Cedar Creek Golf Course","Albertville","MN","763-497-8245","D","1,2,6","71","https://www.cedarcreekgolfmn.com","5700 Jason Ave NE, Albertville, MN 55301",False),
    ("Grandview Lodge - Pines","Nisswa","MN","866-801-2951","D","1,2,6","72","https://www.grandviewlodge.com","23521 Nokomis Ave, Nisswa, MN 56468",False),
    ("Grandview Lodge - Preserve","Nisswa","MN","866-801-2951","D","1,2,6","72","https://www.grandviewlodge.com","23521 Nokomis Ave, Nisswa, MN 56468",False),
    ("Koronis Hills Golf Course","Paynesville","MN","320-243-4111","D","1,2,6","71","https://www.koronishillsgolf.com","29757 State Hwy 23, Paynesville, MN 56362",False),
    ("Majestic Oaks - Crossroads","Ham Lake","MN","763-755-2140","D","1,2,6","","https://www.majesticoaksgolfclub.com","701 Bunker Lake Blvd, Ham Lake, MN 55304",False),
    ("New Richmond Golf Club","New Richmond","WI","715-246-6724","D","1,2,6","72","https://www.nrgolfclub.com","1226 180th St, New Richmond, WI 54017",False),
    ("Riverwood National Golf Course","Otsego","MN","763-271-5000","D","1,2,6","72","https://www.riverwoodnational.com","10247 95th St NE, Monticello, MN 55362",False),
    ("Theodore Wirth Golf Course","Golden Valley","MN","612-230-6528","D","1,2,6","72","https://www.minneapolisparks.org","1301 Theodore Wirth Pkwy, Golden Valley, MN 55440",False),
    # ----- Level E -----
    ("Eagle Creek Golf Course","Willmar","MN","320-235-1166","E","1,6","72","https://www.willmargolf.com","1000 26th Ave NE, Willmar, MN 56201",False),
    ("Eagle Ridge Golf Course","Coleraine","MN","888-307-3245","E","1,6","72","https://www.golfeagleridge.com","Coleraine, MN 55722",False),
    ("Stones Throw Golf Course","Milaca","MN","320-983-2110","E","6","70","https://www.stonesthrowgolf.com","15679 Central Ave, Milaca, MN 56353",True),
    ("Sundance Golf Course","Maple Grove","MN","763-420-4700","E","1,2,6","72","https://www.sundancegolfbowl.com","15240 113th Ave, Maple Grove, MN 55369",False),
    # ----- Level F -----
    ("Bemidji Town & Country Club","Bemidji","MN","218-751-9215","F","1","72","https://www.bemidjigolf.com","Bemidji, MN 56619",False),
    ("Brooktree Golf Course","Owatonna","MN","507-774-7100","F","1,2,6","71","","1369 Cherry St, Owatonna, MN 55060",False),
    ("Chisago Lakes Golf Course","Lindstrom","MN","651-257-1484","F","1,2,6","72","https://www.chisagolakesgolf.com","12975 292nd St, Lindstrom, MN 55045",False),
    ("Clifton Highlands Golf Course","Prescott","WI","715-262-5141","F","1,2,6","72","https://www.cliftonhighlands.com","N6890 1230th St, Prescott, WI 54021",False),
    ("Long Bow Golf Club","Walker","MN","218-547-4121","F","1,2,6","72","https://www.longbowgolfclub.com","15980 Hwy 23 NE, Walker, MN 56484",False),
    ("Mississippi National Golf Links","Red Wing","MN","651-388-1874","F","1,2,6","71","https://www.golfredwing.com","409 Golf Links Dr, Red Wing, MN 55066",False),
    ("Roseville Cedarholm Golf Course","Roseville","MN","651-633-8337","F","1,2,5","27","https://www.cityofroseville.com/golf","2323 Hamline Ave, Roseville, MN 55113",False),
    ("Shoreland Country Club","St Peter","MN","507-931-4400","F","1,2,6","69","https://www.shorelandcc.com","43781 Golf Course Rd, St Peter, MN 56082",False),
    ("Superior National","Lutsen","MN","218-663-7195","F","1,2,6","72","https://www.superiornational.com","Lutsen, MN 55612",False),
    ("Tanners Brook Golf Course","Forest Lake","MN","651-464-2300","F","1,2,6","71","https://www.tannersbrook.com","5810 190th St, Forest Lake, MN 55025",False),
    ("Whitefish Golf Club","Pequot Lakes","MN","218-543-4900","F","1,6","72","https://www.whitefishgolf.com","7883 Cty Rd 16, Pequot Lakes, MN 56472",False),
    # ----- Level G (discounted rate, Mon-Thu) -----
    ("Bunker Hills Golf Club - Regulation","Coon Rapids","MN","763-755-4141","G","","72","https://www.bunkerhillsgolf.com","12800 Bunker Prairie Rd, Coon Rapids, MN 55448",False),
    ("Cragun's - Lehman 18 & Dutch 27","Brainerd","MN","866-988-0562","G","","","https://www.craguns.com","11000 Craguns Dr, Brainerd, MN 56401",False),
    ("Gravel Pit - 13 Hole Course","Brainerd","MN","218-330-5118","G","","","","17300 Gull River Rd, Brainerd, MN 56401",False),
    ("Gravel Pit - 24 Hole Course","Brainerd","MN","218-330-5118","G","","","","17300 Gull River Rd, Brainerd, MN 56401",False),
    ("Troy Burne Golf Club","Hudson","WI","715-381-9800","G","","72","https://www.troyburne.com","295 Lindsay Rd, Hudson, WI 54016",False),
    ("White Eagle Golf Club","Hudson","WI","888-465-3004","G","","72","https://www.whiteeaglegolf.com","316 White Eagle Trl, Hudson, WI 54016",False),
]

# Level G reduced/regular rates (course name -> (reduced, regular))
MGC_G_RATES = {
    "Bunker Hills Golf Club - Regulation": (54, 79),
    "Cragun's - Lehman 18 & Dutch 27": (100, 175),
    "Gravel Pit - 13 Hole Course": (40, 69),
    "Gravel Pit - 24 Hole Course": (70, 99),
    "Troy Burne Golf Club": (100, 147),
    "White Eagle Golf Club": (75, 95),
}

# ---------------------------------------------------------------------------
# Courses that are in BOTH programs: MGC course name -> (PCC tier, PCC note)
# ---------------------------------------------------------------------------
OVERLAP = {
    "Bellwood Oaks Golf Course": ("1", ""),
    "Benson Golf Club": ("1", ""),
    "Blackberry Ridge Golf Club": ("1", ""),
    "Boulder Pointe Golf Club": ("1", ""),
    "Bristol Ridge Golf Course": ("1", ""),
    "Brookland Golf Park": ("1", "Par 3 course"),
    "Bulrush Golf Club": ("1", ""),
    "Centerbrook Golf Course": ("1", ""),
    "Chisago Lakes Golf Course": ("1", ""),
    "Chomonix Golf Course": ("1", ""),
    "Clifton Highlands Golf Course": ("1", ""),
    "Creeks Bend Golf Course": ("1", ""),
    "Eagle Ridge Golf Course": ("1", ""),
    "Elk River Golf Club": ("1", ""),
    "Emerald Greens Golf Course": ("1", ""),
    "Fort Snelling Golf Course": ("1", ""),
    "Glencoe Country Club": ("1", ""),
    "Gopher Hills Golf Course": ("1", ""),
    "Hiawatha Golf Course": ("1", ""),
    "Hidden Greens Golf Course": ("1", ""),
    "Hidden Haven Golf Club": ("1", ""),
    "Koronis Hills Golf Course": ("1", ""),
    "Legacy Golf Course": ("1", ""),
    "Links at Northfork": ("2", ""),
    "Mississippi National Golf Links": ("1", ""),
    "Monticello Country Club": ("1", ""),
    "Mount Frontenac Golf Course": ("1", ""),
    "New Richmond Golf Club": ("2", "PCC covers the Championship 18"),
    "Oak Glen Golf Course": ("2", "PCC covers Championship 18 and Shorty 9"),
    "Oneka Ridge Golf Club": ("1", ""),
    "Purple Hawk Golf Course": ("1", ""),
    "Red Wing Golf Club": ("1", ""),
    "Rich Spring Golf Club": ("1", ""),
    "Riverwood National Golf Course": ("1", ""),
    "Roseville Cedarholm Golf Course": ("1", "9-hole course"),
    "Southbrook Golf Club": ("1", ""),
    "Stones Throw Golf Course": ("1", ""),
    "Superior National": ("RESORT", "$45 surcharge, max 6 rounds/month"),
    "The Ponds Golf Course": ("1", ""),
    "The Refuge Golf Club": ("2", ""),
    "The Summit Golf Club": ("1", ""),
    "Theodore Wirth Golf Course": ("1", "PCC covers the 18-hole course"),
    "Turtleback Golf Course": ("2", ""),
    "Whispering Pines Golf Course": ("1", ""),
    "White Eagle Golf Club": ("3", ""),
}

# ---------------------------------------------------------------------------
# PCC-only courses: (name, city, state, tier, note)
# ---------------------------------------------------------------------------
PCC_ONLY = [
    ("Afton Alps Golf Course","Afton","MN","1",""),
    ("Albion Ridges Golf Course","Annandale","MN","1",""),
    ("Big Fish Golf Club","Hayward","WI","1",""),
    ("Bos Landen Golf Club","Pella","IA","2",""),
    ("Bridges Golf Course","Winona","MN","1",""),
    ("Briggs Woods Golf Course","Webster City","IA","1",""),
    ("Buffalo Heights Golf Course","Buffalo","MN","1","9-hole course"),
    ("Columbia Golf Club","Minneapolis","MN","1","NE Minneapolis"),
    ("Crosswoods Golf Course","Crosslake","MN","1",""),
    ("Crow River Golf Club","Hutchinson","MN","2",""),
    ("Crystal Lake Golf Club","Lakeville","MN","2",""),
    ("Daytona Golf Club","Dayton","MN","1",""),
    ("Dodge Country Club","Dodge Center","MN","1",""),
    ("Drugan's Castle Mound","Holmen","WI","1",""),
    ("Eagle Valley Golf Course","Woodbury","MN","2",""),
    ("Edinburgh USA","Brooklyn Park","MN","3",""),
    ("Enger Park Golf Course","Duluth","MN","1",""),
    ("Fiddlestix Golf Course","Garrison","MN","1","Mille Lacs area"),
    ("Fountain Valley Golf Club","Farmington","MN","1",""),
    ("Fox Run Golf Course","Webster","WI","1",""),
    ("Geneva Golf Club","Alexandria","MN","2",""),
    ("Golden Eagle Golf Club","Crosslake","MN","1","Brainerd area"),
    ("Goodrich Golf Course","St Paul","MN","1",""),
    ("GreyStone Golf Club","Sauk Centre","MN","1",""),
    ("Gross National Golf Club","Minneapolis","MN","2",""),
    ("Hastings Golf Club","Hastings","MN","2","Formerly Dakota Pines GC"),
    ("Hayward Golf Club","Hayward","WI","1",""),
    ("Headwaters Country Club","Park Rapids","MN","1",""),
    ("Heritage Links Golf Club","Lakeville","MN","1",""),
    ("Hidden Greens North Golf Course","Solon Springs","WI","1",""),
    ("Highland 9-Hole Course","St Paul","MN","1",""),
    ("Highland National Golf Course","St Paul","MN","2",""),
    ("Island Lake Golf Course","Shoreview","MN","1",""),
    ("Jewel Golf Club","Lake City","MN","1","5-day advance booking window"),
    ("Kilkarney Hills Golf Club","River Falls","WI","1",""),
    ("Lakeview National Golf Course","Two Harbors","MN","1",""),
    ("Lester Park Golf Course","Duluth","MN","1",""),
    ("Meadow Greens Golf Course","Austin","MN","1",""),
    ("Meadowbrook Golf Club","Hopkins","MN","2",""),
    ("Minnesota National Golf Course","McGregor","MN","2",""),
    ("Montgomery National Golf Club","Montgomery","MN","1",""),
    ("Nemadji Golf Course","Superior","WI","1",""),
    ("New Hope Village Par 3","New Hope","MN","1","Par 3 course"),
    ("Northwood Hills Golf Course","Garrison","MN","1",""),
    ("Oakdale Golf Club","Buffalo Lake","MN","1",""),
    ("Pebble Creek Golf Club","Becker","MN","1","Championship course + Local 9"),
    ("Pebble Lake Golf Club","Fergus Falls","MN","1",""),
    ("Pine Island Golf Course","Pine Island","MN","1",""),
    ("Pinewood Golf Course","Elk River","MN","1","9-hole course"),
    ("Pokegama Golf Course","Grand Rapids","MN","1",""),
    ("Ponds at Battle Creek","Maplewood","MN","1",""),
    ("River Oaks Golf Course - Cottage Grove","Cottage Grove","MN","1","Different course than River Oaks in Cold Spring"),
    ("Riverview Greens Golf Course","Rochester","MN","1",""),
    ("Royal Golf Club","Lake Elmo","MN","3",""),
    ("Ruttger's Bay Lake Lodge - Lakes & Alec's 9","Deerwood","MN","1","Near Mille Lacs"),
    ("St. Croix National Golf Course","Somerset","WI","1",""),
    ("Shadowbrooke Golf Course","Lester Prairie","MN","1",""),
    ("Shamrock Golf Course","Corcoran","MN","1",""),
    ("Silver Bay Golf Course","Silver Bay","MN","1",""),
    ("Siren National Golf Course","Siren","WI","1",""),
    ("South Fork Golf Club","St James","MN","1",""),
    ("Southern Hills Golf Course","Farmington","MN","1","3-day advance booking window"),
    ("Spooner Golf Club","Spooner","WI","1",""),
    ("Stillwater Oaks Golf Course","Stillwater","MN","1",""),
    ("Stonebrooke Golf Club","Shakopee","MN","2","3-day advance booking window"),
    ("Sugarbrooke Golf Course","Cohasset","MN","1","Near Grand Rapids"),
    ("Territory Golf Club","St Cloud","MN","2",""),
    ("The River Golf Course","International Falls","MN","1",""),
    ("Thumper Pond Golf Course","Ottertail","MN","1",""),
    ("Timber Creek Golf Course","Watertown","MN","1",""),
    ("Tipsinah Mounds Golf Course","Elbow Lake","MN","1",""),
    ("Trempealeau Mountain Golf Course","Trempealeau","WI","1",""),
    ("U of M Les Bolstad Golf Course","Minneapolis","MN","1",""),
    ("Valleywood Golf Course","Apple Valley","MN","2",""),
    ("Vintage Golf Course - Executive 18","Otsego","MN","1","Different course than The Vintage GC in Staples"),
    ("Voyager Village Golf Course","Danbury","WI","1","Par 3 course NOT included in PCC"),
    ("Waters Edge Golf Course","Shakopee","MN","1",""),
    ("Wild Marsh Golf Club","Buffalo","MN","2",""),
    ("Willingers Golf Club","Northfield","MN","3",""),
    ("Zumbrota Golf Club","Zumbrota","MN","1",""),
    ("Zumbro Falls Golf Club","Zumbro Falls","MN","1",""),
]

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s

def coords(city, state):
    key = f"{city}|{state}"
    if key not in CITY_COORDS:
        raise SystemExit(f"Missing coordinates for {key} - add it to CITY_COORDS")
    return CITY_COORDS[key]

courses = []
seen = set()

# Match OVERLAP keys against MGC names loosely (MGC names sometimes carry suffixes
# like "(River Valley Golf Trail)").
def overlap_for(mgc_name):
    for key, val in OVERLAP.items():
        if mgc_name.startswith(key) or key.startswith(mgc_name):
            return val
    return None

for (name, city, st, phone, level, carts, par, website, address, rar) in MGC_COURSES:
    lat, lng = coords(city, st)
    cart_codes = [c for c in carts.split(",") if c]
    mgc = {
        "level": level,
        "levelText": MGC_LEVELS[level],
        "cartCodes": cart_codes,
        "cartNotes": [MGC_CART_LEGEND[c] for c in cart_codes],
        "rideARound": rar,
        "offer": ("Discounted rate Mon-Thu (see rates) - 4 rounds, up to 2 per visit"
                  if level == "G" else
                  "2-for-1: one free 18-hole green fee with paid fee of equal/greater value, up to 4x. Plus 4x $5 cart discounts and 4x 2-for-1 range balls (course exceptions apply)."),
    }
    if name in MGC_G_RATES:
        red, reg = MGC_G_RATES[name]
        mgc["reducedRate"] = red
        mgc["regularRate"] = reg
    ov = overlap_for(name)
    pcc = None
    if ov:
        tier, note = ov
        pcc = {"tier": tier, "tierText": PCC_TIERS[tier], "note": note}
    c = {
        "id": slug(name),
        "name": name,
        "city": city, "state": st,
        "lat": lat, "lng": lng,
        "coordSource": "city-approximate",
        "address": address, "phone": phone,
        "website": website, "par": par,
        "mgc": mgc, "pcc": pcc,
    }
    courses.append(c)
    seen.add(slug(name))

for (name, city, st, tier, note) in PCC_ONLY:
    sid = slug(name)
    if sid in seen:
        raise SystemExit(f"Duplicate id: {sid}")
    lat, lng = coords(city, st)
    courses.append({
        "id": sid, "name": name, "city": city, "state": st,
        "lat": lat, "lng": lng, "coordSource": "city-approximate",
        "address": "", "phone": "", "website": "", "par": "",
        "mgc": None,
        "pcc": {"tier": tier, "tierText": PCC_TIERS[tier], "note": note},
    })
    seen.add(sid)

courses.sort(key=lambda c: c["name"].lower())

out = {
    "meta": {
        "updated": "2026-07-02",
        "season": "2026",
        "sources": {
            "mgc": "https://minnesotagolfcard.com",
            "pcc": "https://www.thepubliccc.com",
        },
        "disclaimer": "Community-built planning tool. Offers, restrictions and participation change - always verify with the course and the official program sites before playing.",
        "mgcLevels": MGC_LEVELS,
        "mgcCartLegend": MGC_CART_LEGEND,
        "pccTiers": PCC_TIERS,
        "mgcCardNotes": "2026 card: $40. Digital card, each course accepts it 4 times. Ride-a-Round: one-time free golf for up to 4 people (cart rental required), Mon-Fri only, before May 15 or after Sept 15.",
        "pccMembershipNotes": "$89 one-time joining fee + $65/month year-round. Max 12 rounds/month per course (Tier 1-3). Blackouts Sat/Sun/holidays: 7-11 am (Tier 1) or 7 am-12 pm (Tier 2+). Member ID card required.",
    },
    "courses": courses,
}

json_text = json.dumps(out, indent=2)

# The app loads its data through a plain <script> tag (see index.html) so that
# it works even when you just double-click index.html. A <script> can load a
# local file; fetch() cannot. Everything after the first line below is ordinary
# JSON you can edit by hand - just leave the "window.GVM_DATA =" line and the
# final ";" alone.
with open("data/courses.js", "w") as f:
    f.write("window.GVM_DATA =\n")
    f.write(json_text)
    f.write("\n;\n")

# Also write plain JSON, handy for validating at jsonlint.com or reusing elsewhere.
with open("data/courses.json", "w") as f:
    f.write(json_text)

mgc_n = sum(1 for c in courses if c["mgc"])
pcc_n = sum(1 for c in courses if c["pcc"])
both_n = sum(1 for c in courses if c["mgc"] and c["pcc"])
print(f"Wrote data/courses.js and data/courses.json: {len(courses)} courses "
      f"({mgc_n} MN Golf Card, {pcc_n} PCC, {both_n} in both)")
