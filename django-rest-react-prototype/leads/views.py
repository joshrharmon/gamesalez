from django.shortcuts import render
from .models import Lead
from .serializers import LeadSerializer
from rest_framework import generics

from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from rest_framework import permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer, UserSerializerWithToken

import sqlite3
from sqlite3 import Error


# Create your views here.
class LeadListCreate(generics.ListCreateAPIView):
  permission_classes = (permissions.AllowAny,)
  queryset = Lead.objects.all()
  serializer_class = LeadSerializer


# get the current username and return it (note this is not the steam name)
@api_view(['GET'])
def current_user(request):
  """
  Determine the current user by their token, and return their data
  """

  serializer = UserSerializer(request.user)
  return Response(serializer.data)


class UserList(APIView):
  """
  Create a new user. It's called 'UserList' because normally we'd have a get
  method here too, for retrieving a list of all User objects.
  """

  permission_classes = (permissions.AllowAny,)

  def get(self, request, format=None):
    """
    Return a list of all users.
    """

    usernames = [user.username for user in User.objects.all()]
    return Response(usernames)

  def post(self, request, format=None):
    serializer = UserSerializerWithToken(data=request.data)
    if serializer.is_valid():
      serializer.save()
      return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# connect to the database
def create_conn(path):
  connection = None
  try:
    connection = sqlite3.connect(path, check_same_thread=False)
    print("DB connection successful.")
  except Error as e:
    print(f"An error '{e}' occurred during db connection")
  return connection

# get the steamID of the current user and return it
@api_view(['GET'])
def steamID(request):
  username = request.user

  with create_conn("db.sqlite3") as conn:
    cursor = conn.execute("SELECT id FROM auth_user WHERE username='{}';"
        .format(username))
    userid = cursor.fetchall()[0][0]

    stmt = """SELECT claimed_id FROM django_openid_auth_useropenid WHERE
      id={};""".format(userid)
    cursor = conn.execute(stmt)
    steamid = cursor.fetchall()[0][0]


  return Response(steamid[37:])

# REST endpoint for liking a game
@api_view(['POST'])
def like(request):
  tags = request.data['tags'];
  steamid = request.data['steamid'];

  affinities = {
      'action': 0
    , 'indie': 0
    , 'adventure': 0
    , 'rpg': 0
    , 'horror': 0
    , 'mystery': 0
    , 'simulation': 0
    , 'sports': 0
    , 'racing': 0
    , 'shooter': 0
    , 'strategy': 0
    , 'fighting': 0
    , 'retro': 0
    , 'anime': 0
    , 'other': 0
  }

  # update database
  with create_conn("db.sqlite3") as conn:
    row = conn.execute("SELECT * FROM gc_userData WHERE username=?"
        , (steamid,)).fetchone()

    if row:
      affinities['action'] = row[1]
      affinities['indie'] = row[2]
      affinities['adventure'] = row[3]
      affinities['rpg'] = row[4]
      affinities['horro'] = row[5]
      affinities['mystery'] = row[6]
      affinities['simulation'] = row[7]
      affinities['sports'] = row[8]
      affinities['racing'] = row[9]
      affinities['shooter'] = row[10]
      affinities['strategy'] = row[11]
      affinities['fighting'] = row[12]
      affinities['retro'] = row[13]
      affinities['anime'] = row[14]

    affinities[getGenre(tags)] = 1

    conn.execute("DELETE FROM gc_userData WHERE username=?", (steamid,))
    conn.execute("INSERT INTO gc_userData VALUES"
      + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
      , (steamid, affinities['action'], affinities['indie']
      , affinities['adventure'], affinities['rpg'], affinities['horror']
      , affinities['mystery'], affinities['simulation'], affinities['sports']
      , affinities['racing'], affinities['shooter'], affinities['strategy']
      , affinities['fighting'], affinities['retro'], affinities['anime']))

  return Response()


# REST endpoint for processing the wishlist for the recommendations engine
@api_view(['POST'])
def processWishlist(request):
  wishlist = request.data['wishlist'];
  steamid = request.data['steamid'];

  affinities = {
      'action': 0
    , 'indie': 0
    , 'adventure': 0
    , 'rpg': 0
    , 'horror': 0
    , 'mystery': 0
    , 'simulation': 0
    , 'sports': 0
    , 'racing': 0
    , 'shooter': 0
    , 'strategy': 0
    , 'fighting': 0
    , 'retro': 0
    , 'anime': 0
    , 'other': 0
  }

  for game in wishlist:
    tags = game['tags']
    genre = getGenre(tags)
    # affinities[genre] += 1
    affinities[genre] = 1

  with create_conn("db.sqlite3") as conn:
    conn.execute("DELETE FROM gc_userData WHERE username=?", (steamid,))
    conn.execute("INSERT INTO gc_userData VALUES"
      + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
      , (steamid, affinities['action'], affinities['indie']
      , affinities['adventure'], affinities['rpg'], affinities['horror']
      , affinities['mystery'], affinities['simulation'], affinities['sports']
      , affinities['racing'], affinities['shooter'], affinities['strategy']
      , affinities['fighting'], affinities['retro'], affinities['anime']))

  return Response()

genreMap = {
    'Adventure': 'adventure'
  , 'Exploration': 'adventure'
  , 'Open World': 'adventure'
  , '4X': 'strategy'
  , 'Grand Strategy': 'strategy'
  , 'Tactical RPG': 'rpg'
  , 'City Builder': 'simulation'
  , 'Action': 'action'
  , 'Roguelike': 'rpg'
  , 'RPG': 'rpg'
  , 'Strategy': 'strategy'
  , 'Simulation': 'simulation'
  , 'Indie': 'indie'
  , 'Racing': 'racing'
  , 'Sports': 'sports'
  , 'Horror': 'horror'
  , 'Retro': 'retro'
  , 'Fighting': 'fighting'
  , 'Third-Person Shooter': 'shooter'
  , 'Top-Down Shooter': 'shooter'
  , 'Shooter': 'shooter'
  , 'Anime': 'anime'
  , 'Mystery': 'mystery'
  , 'Action-Adventure': 'action'
  , 'Psychological Horror': 'horror'
}

supportedGenres = [
    'action'
  , 'indie'
  , 'adventure'
  , 'rpg'
  , 'horror'
  , 'mystery'
  , 'simulation'
  , 'sports'
  , 'racing'
  , 'shooter'
  , 'strategy'
  , 'fighting'
  , 'retro'
  , 'anime'
]

# get the first supported genre from this list of tags, or 'other' if none were
# supported
def getGenre(tags):
  for tag in tags:
    # we need to check which form it is to get around this somewhat awkward
    # capitalization problem.
    if tag[:1].isupper():
      if tag in genreMap.keys():
        genre = genreMap[tag]
        if genre in supportedGenres:
          return genre
    else:
      return tag
  return 'other'
