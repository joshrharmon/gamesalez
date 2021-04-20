import requests, json, re, schedule, time, sqlite3

from flask import Flask
from sqlite3 import Error
from flask_restful import Resource, Api, reqparse
from bs4 import BeautifulSoup

# Put in DB
steamCategoryID = {
	"action": 19,
	"indie": 492,
	"adventure": 21,
	"rpg": 122,
	"horror": 1667,
	"mystery": 5716,
	"simulation": 599,
	"sports": 701,
	"racing": 699,
	"shooter": 1774,
	"strategy": 9,
	"fighting": 1743,
	"retro": 4004,
	"anime": 4085
}

API_KEY='4ca42d11f7def3c9d0eea805aa48413a2c5ec7e6'
DB_PATH='../django-rest-react-prototype/db.sqlite3'

app = Flask(__name__)
api = Api(app)

class gameFetch():
	def __init__(self, api_key, db_path):
		self.api_key = api_key
		self.db_path = db_path

	def create_conn(self, path):
		connection = None
		try:
			connection = sqlite3.connect(path, check_same_thread=False)
			print("DB connection successful.")
		except Error as e:
			print(f"Sorry, an error occurred during Database connection")
		return connection

	"""
	apiStatus - Returns API response or error code
	param status: Takes in request object from Python API request
	return status: Prints API JSON body if successful (200), else returns appropriate error code
	"""
	def apiStatus(self, status):
		if status.status_code == 200:
			return status.json()
		else:
			returnMsg = ":: API fetch failed with error code: " + str(status)
			print(returnMsg)

	"""
	gameList - If string contains commas (indicating multiple game queries), replace with appropriate string
	param games: list of game(s)
	return games: Properly formatted string to execute a multi-return API request
	"""
	def gameList(self, games):
		gameFormat = ""
		if "," in games:
			gameFormat = games.replace(",","%2C")
		if "/" in games:
			gameFormat = games.replace("/", "%2F")
		if " " in games:
			gameFormat = games.replace(" ", "%20")
		else:
			gameFormat = games
		return gameFormat
		
	"""
	priceFormat - Formats non-US prices to work with program
	param price: String of price
	"""
	def priceFormat(self, price):
		pure = []
		priceDec = ""
		repl = re.sub(",", ".", price)
		strip = re.findall(r"""(\D?){1}(\d+)(.)(\d+)(\D?){1}""", repl)
		pure.append(strip[0][0]) if strip[0][0] != '' else pure.append(strip[0][len(strip[0]) - 1])
		for elem in range(1, len(strip[0]) - 1):
			priceDec += strip[0][elem]
		pure.append(priceDec)
		return pure

	"""
	gameGET - Returns basic metadata about game (does not include prices)
	param apiKey: API key for making request
	param gameTitle: single, non-spaced game titles or multiple game titles separated by commas
		(e.g. dishonored OR amongus,dishonored,etc)
	"""
	def gameGET(self, api_key, gameTitle):
		gameFormat = gameList(gameTitle)
		apiRequest = "https://api.isthereanydeal.com/v01/game/info/?key=" + api_key + "&plains=" + gameFormat
		return apiStatus(requests.get(apiRequest))

	"""
	gameLowest - Will return a game(s) lowest-ever price
	param apiKey: API key for making request
	param gameTitle: single, non-spaced game titles or multiple game titles separated by commas
		(e.g. dishonored OR amongus,dishonored,etc)
	"""
	def gameLowest(self, api_key, gameTitle):
		gameFormat = gameList(gameTitle)
		apiRequest = "https://api.isthereanydeal.com/v01/game/lowest/?key=" + api_key + "&plains=" + gameFormat + "&region=us&country=US&shops=steam"
		return apiStatus(requests.get(apiRequest))

	"""
	getPlains - Will return a game(s) "plain" titles based on ID
	param apiKey: API key for making request
	param ids: ids in the format of app/12345
	"""
	def getPlains(self, api_key, ids):
		idFormat = gameList(ids)
		apiRequest = "https://api.isthereanydeal.com/v01/game/plain/id/?key=" + api_key + "&shop=steam&ids=" + idFormat
		plainsDict = requests.get(apiRequest).json()
		return plainsDict.get('data').get(ids)

	"""
	retrieveMeta - Multi-purpose function to retrieve specific info on a game.
	param gameURL: Direct link to Steam game
	param dataType: "art" to get direct link to cover art, "html" to retrieve html data
	"""
	def retrieveMeta(self, gameURL, dataType, HTMLdata):
		if dataType == "html":
			return requests.get(gameURL).content
		else:
			soup = BeautifulSoup(HTMLdata, 'html.parser').head
			if gameURL != None and dataType == "art":
				# TOFIX: Find specific image tag and get attribute
				# If temporary HTML fetch error occurs, re-fetch
				if soup == None:
					tempHTML = self.retrieveMeta(gameURL, "html", None)
					self.retrieveMeta(gameURL, "art", tempHTML)
				else:
					temp = soup.find_all("link")[-1]
					return re.findall(r"http.*\d+", str(temp))[0]

	"""
	dbForm - Escapes special characters
	param text - Text to inspect
	return text - Escaped characters in string if applicable
	"""
	def dbForm(self, text):
		if "'" in text:
			return text.replace("'","''")
		else:
			return text

	"""
	dbInit - Will create and initialize tables
	"""
	def dbInit(self):
		with self.create_conn(self.db_path) as con:
			con.execute('''DROP TABLE IF EXISTS 'webpage';''')
			con.execute('''CREATE TABLE 'webpage' (
							'gameID' int PRIMARY KEY,
							'title' VARCHAR(255) NOT NULL,
							'category' VARCHAR(32) NOT NULL,
							'currency' CHAR(1) NOT NULL,
							'price_old' float NOT NULL,
							'price_new' float NOT NULL,
							'price_cut' smallint NOT NULL,
							'url' VARCHAR(255) NOT NULL,
							'art' VARCHAR(255)
							);''')

	"""
	steamDBFetch - Will fetch numGmaes from APIs and Steam and update DB every 6 hours
	param numGames: Amount of games to fetch from Steam and APIs
	param category: Specify front, action, indie, adventure, etc. to get a narrowed result
	"""
	def steamDBFetch(self, category, numGames=6):
		print("Fetching " + str(numGames) + " games from category " + str(category) + "...")
		with self.create_conn(self.db_path) as con:
			gamesFetched = 0
			gameItems = numGames
			steamFetch = "https://store.steampowered.com/search/?specials=1" if "front" in category else "https://store.steampowered.com/search/?tags={}&specials=1".format(steamCategoryID.get(category))
			soup = BeautifulSoup(requests.get(steamFetch).content, features="html.parser")
			gameData = soup.find_all("a", class_="search_result_row ds_collapse_flag")
			gameTitles = soup.find_all("span", class_="title")
			gameOldPrices = soup.find_all("strike")
			gameNewPrices = soup.find_all("div", class_="col search_price discounted responsive_secondrow")
			while gamesFetched < gameItems:
				url = gameData[gamesFetched]['href']

				# Fetch HTML for game page for scraping
				gameHTML = self.retrieveMeta(url, "html", None)
				soup = BeautifulSoup(gameHTML, 'html.parser')

				title = gameTitles[gamesFetched].contents[0]
				currency = self.priceFormat(gameOldPrices[gamesFetched].contents[0])[0]
				price_old = self.priceFormat(gameOldPrices[gamesFetched].contents[0])[1]
				price_new = self.priceFormat(gameNewPrices[gamesFetched].contents[-1].strip())[1]
				price_cut = round(100.00 - ((float(price_new) * 100) / (float(price_old))))

				art = self.retrieveMeta(url, "art", gameHTML)
				
				# Insert into db
				con.execute("INSERT INTO webpage(title, category, currency, price_old, price_new, price_cut, url, art) VALUES(?,?,?,?,?,?,?,?)", (title, category, currency, price_old, price_new, price_cut, url, art))
				gamesFetched += 1
	"""
	steamDBResp - Will access the SQLite DB and form a JSON response for the frontend to fetch
	param numGames: Amount of games to fetch
	return: JSON response for numGames
	"""
	def steamDBResp(self, category, numGames=6):
		with self.create_conn(self.db_path) as con:
			JSONData = []
			sqlFetch = "SELECT * FROM webpage WHERE category='{}' LIMIT '{}'".format(category, numGames)
			cursor = con.execute(sqlFetch)
			for row in cursor:
				gameJSON = dict()
				gameJSON["title"] = row[1]
				gameJSON["category"] = row[2]
				gameJSON["currency"] = row[3]
				gameJSON["price_old"] = row[4]
				gameJSON["price_new"] = row[5]
				gameJSON["price_cut"] = row[6]
				gameJSON["url"] = row[7]
				gameJSON["art"] = row[8]
				JSONData.append(gameJSON)
			return JSONData
			
	"""
	Main program:
	- Initialize DB with tables
	- Start scheduler to refresh DB every hour with 6 games by default
	- Will fetch all categories on initial run, 10 games each
	- Start Flask server
	- Make sure scheduler continues to check for pending tasks if missed
	"""		
	def start(self):
		self.dbInit()
		self.steamDBFetch("front")
		schedule.every().hour.do(self.steamDBFetch, "front")

		for key in steamCategoryID:
			self.steamDBFetch(key, 10)
			schedule.every().hour.do(self.steamDBFetch, key, 10)

		api.add_resource(Deals, '/deals')
		api.add_resource(Lowest,'/lowest')

"""
Deals - Outward API call to give all relevant game data to front-end
param num: Number of games to return
return JSON, statuscode: The JSON response and status code
"""
class Deals(Resource):
	def get(self):
		parser = reqparse.RequestParser()
		parser.add_argument('num', required=True)
		parser.add_argument('cat')
		args = parser.parse_args()
		return json.loads(json.dumps(gameFetch(API_KEY, DB_PATH).steamDBResp(args['cat'], int(args['num'])))), 200

"""
OBSOLETE - Based on older code, not in use in this version.
Lowest - Outward API call to give lowest price for list of games
param games: List of games to query (game1,game2,...) in 'plains' format
return JSON, statuscode: The JSON response and status code
"""
class Lowest(Resource):
	def get(self):
		parser = reqparse.RequestParser()
		parser.add_argument('games', required=True)
		args = parser.parse_args()
		rawData = gameLowest(API_KEY, args['games']).get('data')
		for game in rawData.items():
			gameData = game[1].get('list')[0]
			html = retrieveMeta(gameData["url"], "html", None)
			gameData["art"] = retrieveMeta(gameData["url"], "art", html)
		jsonData = json.dumps(rawData)
		jsonObj = json.loads(jsonData)
		return jsonObj, 200