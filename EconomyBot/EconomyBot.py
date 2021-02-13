import os
import discord
import datetime
import json
from discord.ext import commands
from io import StringIO
bot = commands.Bot(command_prefix='-')
client = discord.Client()

QuestPostingChannel = None
QuestCreationChannel = None
CharacterCreationChannel = None
InventoryManagementChannel = None

SuperAdmins = ["slackerlife#7167"]

LeveltoXP = {
    0           :       1,
    300         :       2,
    900         :       3,
    2700        :       4,
    6500        :       5,
    14000       :       6,
    23000       :       7,
    34000       :       8,
    48000       :       9,
    64000       :       10,
    85000       :       11,
    100000      :       12,
    120000      :       13,
    140000      :       14,
    165000      :       15,
    195000      :       16,
    225000      :       17,
    265000      :       18,
    305000      :       19,
    355000      :       20
}



# quest-board-bot
# 1. DM creates a quest posting with -createquest [Name] [Description] [Tier] [Date/Time] [Player Count]
# 2. Player asks DM to join with [Character Name]
# 3. DM sends bot -join [Discord Name] [Character Name]
# 4. After quest, DM sends bot -distribute
#   -> Any additional items players received are added manually
#
# Per character sheet manager
# For each character . . . 
# 1. XP
# 2. Money
# 3. Items

@bot.command()
async def designate(ctx, name):
    if IsAdmin(ctx) == False:
        return
    global QuestCreationChannel
    global QuestPostingChannel
    global CharacterCreationChannel
    global InventoryManagementChannel
    CreateOrExistsSetupFolder()
    setupDictionary = dict()

    setupDictionary = {"QuestCreationChannel": "", "QuestPostingChannel": "", 
                       "CharacterCreationChannel": "", "InventoryManagementChannel": ""}

    with open("./setup.json") as fob:
        if(os.stat("./setup.json").st_size > 0):
            setupDictionary = json.load(fob)

    setupDictionary[name] = ctx.channel.name

    if name == "QuestCreationChannel":
        QuestCreationChannel = setupDictionary[name]
    elif name == "QuestPostingChannel":
        QuestPostingChannel = setupDictionary[name]
    elif name == "CharacterCreationChannel":
        CharacterCreationChannel = setupDictionary[name]
    elif name == "InventoryManagementChannel":
        InventoryManagementChannel = setupDictionary[name]
        
    io = StringIO()
    data = json.dump(setupDictionary, io)

    with open("./setup.json", "w") as fob:
        fob.write(io.getvalue())
    return

# Create a quest
@bot.command()
async def createquest(ctx, name, description, tier, time, maxPlayers = 5, additionalGold = "", additionalItems = "",  reservedPlayers = ""):
    global QuestCreationChannel
    global QuestPostingChannel
    if(ctx.channel.name != QuestCreationChannel):
        return
    file = CreateOrExistsQuest(ctx, name)
    questDictionary = {"Name": str(name), "Tier": str(tier), "Time": str(time), "Description": str(description), "AdditionalGold": additionalGold, "AdditionalItems": additionalItems, "MaxPlayers": str(maxPlayers), "Players": reservedPlayers, 
      "MessageID": ""}

    postingChannel = discord.utils.get(bot.get_all_channels(), name=QuestPostingChannel)

    postFormat = GetQuestMessage(questDictionary)

    postMessage = await postingChannel.send(postFormat)

    questDictionary["MessageID"] = postMessage.id
    
    io = StringIO()
    data = json.dump(questDictionary, io)

    with open(file, "w") as fob:
        fob.write(io.getvalue())

        
# Create a quest
@bot.command()
async def unsignup(ctx, characterName, questName):
    if(ctx.channel.name != QuestPostingChannel):
        return
    
    file = CreateOrExistsQuest(ctx, questName)
    if(os.path.exists(file) == False):
        await ctx.channel.send("Couldn't find a quest called " + questName + ".")
        return

    questDictionary = {"Name": "", "Tier": "", "Time": "", "Description": "", "AdditionalGold": "", "AdditionalItems": "", "MaxPlayers": "",  "Players": "", "MessageID": ""}

    with open(file, "r") as fob:
        questDictionary = json.load(fob)
    
    signupval = characterName + " (" + str(ctx.author) + "),"
    if signupval in questDictionary["Players"]:
        questDictionary["Players"] = questDictionary["Players"].replace(signupval, '') 
        
    io = StringIO()
    data = json.dump(questDictionary, io)

    with open(file, "w") as fob:
        fob.write(io.getvalue())
    msg = await ctx.fetch_message(int(questDictionary["MessageID"]))
    await msg.edit(content=GetQuestMessage(questDictionary))

# Create a quest
@bot.command()
async def signup(ctx, characterName, questName):
    if(ctx.channel.name != QuestPostingChannel):
        return
    
    file = CreateOrExistsQuest(ctx, questName)
    if(os.path.exists(file) == False):
        await ctx.channel.send("Couldn't find a quest called " + questName + ".")
        return

    questDictionary = {"Name": "", "Tier": "", "Time": "", "Description": "", "AdditionalGold": "", "AdditionalItems": "", "MaxPlayers": "",  "Players": "", "MessageID": ""}

    with open(file, "r") as fob:
        questDictionary = json.load(fob)
       
    if(GetCharacterExists(ctx, characterName) == False):
        await ctx.channel.send("You do not have a character named " + characterName + ".")
        return

    folder = GetCharacterFolder(ctx, characterName)
        
    reserves = questDictionary["Players"].split(',')
    reserves.remove("")
    reservesCount = len(reserves)
    
    if(reservesCount >= int(questDictionary["MaxPlayers"])):
        await ctx.channel.send(questDictionary["Name"] + " is full.")
        return

    signupval = str(ctx.author)
    if signupval in questDictionary["Players"]:
        return
    questDictionary["Players"] += characterName + " (" + str(ctx.author) + "),"
    
    io = StringIO()
    data = json.dump(questDictionary, io)

    with open(file, "w") as fob:
        fob.write(io.getvalue())
    msg = await ctx.fetch_message(int(questDictionary["MessageID"]))
    await msg.edit(content=GetQuestMessage(questDictionary))
    
# Finish a quest
@bot.command()
async def finishquest(ctx, questName):
    if(ctx.channel.name != QuestPostingChannel):
        return
    
    file = CreateOrExistsQuest(ctx, questName)
    if(os.path.exists(file) == False):
        await ctx.channel.send("Couldn't find a quest called " + questName + ".")
        return

    questDictionary = {"Name": "", "Tier": "", "Time": "", "Description": "", "AdditionalGold": "", "AdditionalItems": "", "MaxPlayers": "",  "Players": "", "MessageID": ""}

    with open(file, "r") as fob:
        questDictionary = json.load(fob)

    players = questDictionary["Players"].split(',')
    for entry in players:
        pair = entry.split('(')
        if pair[0] == '':
            continue
        characterName = pair[0].lstrip(' ').rstrip(' ')
        playerAccount = pair[1].replace(')', '').replace(' ', '')
        characterData = dict()
        inventoryData = dict()
        characterFolder = playerAccount + "/" + characterName + "/"
        characterFile = characterFolder + characterName + ".json"
        characterInventory = characterFolder + "balance.json"
        with open(characterFile) as fob:
            characterData = json.load(fob)
        currentXP = int(characterData["XP"])
        characterLevel = GetCharacterLevel(currentXP)
        characterData["XP"] = str(currentXP + 300 * characterLevel)
        io = StringIO()
        data = json.dump(characterData, io)

        with open(characterFile, "w") as fob:
            fob.write(io.getvalue())
            
        with open(characterInventory) as fob:
            inventoryData = json.load(fob)

        currentGold = int(inventoryData["GoldBalance"])
        inventoryData["GoldBalance"] = str(currentGold + 100 * characterLevel)
        
        io = StringIO()
        data = json.dump(inventoryData, io)

        with open(characterInventory, "w") as fob:
            fob.write(io.getvalue())

def GetCharacterLevel(xp):
    global LeveltoXP
    lastLevel = 1
    for xpBracket in LeveltoXP:
        if(xpBracket > xp):
            return lastLevel
        lastLevel = LeveltoXP[xpBracket]
    return lastLevel

# Create a character
@bot.command()
async def create(ctx, name, backstory):
    if(ctx.channel.name != CharacterCreationChannel):
        return
    folder = GetCharacterFolder(ctx, name)
    characterDictionary = {"Name": str(name), "Backstory": str(backstory), "XP": str(900)}
    
    io = StringIO()
    data = json.dump(characterDictionary, io)

    with open(folder + "/" + characterDictionary["Name"] + ".json", "w") as fob:
        fob.write(io.getvalue())

    DoDeposit(ctx, folder, characterDictionary["Name"], "0")

    await ctx.channel.send("You created " + name + ".")


@bot.command()
async def deposit(ctx, name, amount):
    if(ctx.channel.name != InventoryManagementChannel):
        return
    
    folder = GetCharacterFolder(ctx, name)
    if(os.path.exists(folder) == False):
        await ctx.channel.send("Could not find a characeter named " + name)
        return
    
    await ctx.channel.send("You deposited " + DoDeposit(ctx, folder, name, amount))

def DoDeposit(ctx, folder, name, amount):
    isMoney = False
    logMessage = str(amount)
    if amount.isdigit():
        isMoney = True
        logMessage += " gold"
    
    itemDictionary = {"GoldBalance": "0", "Items": ""}
    balanceFile = folder + "/balance.json"

    if(os.path.exists(balanceFile)):
        with open(balanceFile) as fob:
            itemDictionary = json.load(fob)

    if isMoney:
        itemDictionary["GoldBalance"] = str(int(itemDictionary["GoldBalance"]) + int(amount))
    else:
        if itemDictionary["Items"] != "":
            itemDictionary["Items"] += "|" + amount
        else:
            itemDictionary["Items"] = amount
    
    with open(folder + "/log.txt", "a+") as fob:
        fob.writelines(str(datetime.datetime.now()) + ": [DEPOSIT] " + logMessage + "\n")
        
    io = StringIO()
    data = json.dump(itemDictionary, io)

    with open(balanceFile, "w") as fob:
        fob.write(io.getvalue())
    return logMessage

@bot.command()
async def withdraw(ctx, name, amount):
    if(ctx.channel.name != InventoryManagementChannel):
        return
    
    folder = GetCharacterFolder(ctx, name)
    if(os.path.exists(folder) == False):
        await ctx.channel.send("Could not find a characeter named " + name)
        return
    
    await ctx.channel.send(DoWithdraw(ctx, folder, name, amount))
    
def DoWithdraw(ctx, folder, name, amount):
    isMoney = False
    logMessage = str(amount)
    if amount.isdigit():
        isMoney = True
        logMessage += " gold"
    
    itemDictionary = {"GoldBalance": "0", "Items": ""}
    balanceFile = folder + "/balance.json"

    if(os.path.exists(balanceFile)):
        with open(balanceFile) as fob:
            itemDictionary = json.load(fob)

    if isMoney:
        if(int(itemDictionary["GoldBalance"]) - int(amount) < 0):
            logMessage += " cannot be withdrawn due to insufficient funds."
        else:
            curAmt = str(int(itemDictionary["GoldBalance"]) - int(amount))
            itemDictionary["GoldBalance"] = curAmt
            logMessage += " has been withdrawn. Current balance: " + curAmt
    else:
        if(amount in itemDictionary["Items"]):
            itemDictionary["Items"] = itemDictionary["Items"].replace(amount, '', 1)
            logMessage += " has been removed from your inventory."
        else:
            logMessage += " does not exist in your inventory."
    with open(folder + "/log.txt", "a+") as fob:
        fob.writelines(str(datetime.datetime.now()) + ": [WITHDRAW] " + logMessage + "\n")
        
    io = StringIO()
    data = json.dump(itemDictionary, io)

    with open(balanceFile, "w") as fob:
        fob.write(io.getvalue())
    return logMessage
@bot.command()
async def inventory(ctx, name):
    if(ctx.channel.name != InventoryManagementChannel):
        return
    itemDictionary = {"GoldBalance": "0", "Items": ""}
    if(os.path.exists(GetCharacterFolder(ctx, name) + "/balance.json")):
        with open(GetCharacterFolder(ctx, name) + "/balance.json", "r+") as fob:
            itemDictionary = json.load(fob)
                
    await ctx.channel.send(str(ctx.author) + " your character " + name + "'s current balance is. . . ")
    await ctx.channel.send(itemDictionary["GoldBalance"] + "gp")
    await ctx.channel.send("Items. . .")
    itemList = itemDictionary["Items"].split('|')
    for item in itemList:
        if item != "":
            await ctx.channel.send(item)

@bot.command()
async def give(ctx, amount, player, name):
    if(ctx.channel.name != InventoryManagementChannel):
        return
    #withdraw(ctx, amount)
    s = str(player)[3:-1]
    person = bot.get_all_members()
     # await bot.fetch_user(int(s))
    if person is None:
        await ctx.channel.send(player + " does not exist.")
        return
    await ctx.channel.send(person + " vs " + str(ctx.author))
    return

def GetQuestMessage(questDictionary):
    signedUp = ""
    reserves = questDictionary["Players"].split(',')
    reserves.remove("")
    reservesCount = len(reserves)
    for i in range(int(questDictionary["MaxPlayers"])):
        playerName = ""
        if(i < reservesCount):
            playerName = reserves[i]
        signedUp += "\n" + str(i + 1) + ". " + playerName

    return questDictionary["Name"] + " (Tier " + questDictionary["Tier"] + ")\n" + questDictionary["Time"] + "\n\n" + questDictionary["Description"] + "\n\nPlayers: " + signedUp

def ConvertJSONtoPythonDictionary(data):
    outDict = dict()
    for key, value in data.items():
        outDict[key] = value

def GetUserFolder(ctx):
    author = str(ctx.author)
    if CreateOrExistsUserFolder(ctx):
        return  author + "/"

def CreateOrExistsUserFolder(ctx):
    author = str(ctx.author)
    if not os.path.exists(author):
        os.mkdir(author)
    return True

def CreateOrExistsQuestFolder(ctx):
    if not os.path.exists("./Quests"):
        os.mkdir("./Quests")
    return "./Quests"

def GetCharacterFolder(ctx, name):
    CreateOrExistsCharacter(ctx, name)
    userFolder = GetUserFolder(ctx)
    return userFolder + "/" + name;

def GetCharacterExists(ctx, name):
    userFolder = GetUserFolder(ctx)
    character = userFolder + "/" + name + "/" + name + ".json"
    if not os.path.exists(character):
        return False
    return True

def CreateOrExistsCharacter(ctx, name):
    CreateOrExistsUserFolder(ctx)
    userFolder = GetUserFolder(ctx)
    if not os.path.exists(userFolder + "/" + name):
        os.mkdir(userFolder + "/" + name)
    return True

def CreateOrExistsQuest(ctx, name):
    questFile = CreateOrExistsQuestFolder(ctx) + "/" + str(name) + ".json"
    if not os.path.exists(questFile):
        fob = open(questFile, "w")
        fob.close()
    return questFile

def CreateOrExistsSetupFolder():
    if not os.path.exists("./setup.json"):
        fob = open("./setup.json", "w")
        fob.close()
        return False
    return True

def TryLoadSetup():
    global QuestCreationChannel
    global QuestPostingChannel
    global CharacterCreationChannel
    global InventoryManagementChannel
    with open("./setup.json") as fob:
        if(os.stat("./setup.json").st_size > 0):
            data = json.load(fob)
            QuestCreationChannel = data["QuestCreationChannel"]
            QuestPostingChannel = data["QuestPostingChannel"]
            CharacterCreationChannel = data["CharacterCreationChannel"]
            InventoryManagementChannel = data["InventoryManagementChannel"]

    return True

def IsAdmin(ctx):
    return str(ctx.author) in SuperAdmins


if(CreateOrExistsSetupFolder()):
    TryLoadSetup()

# load your bot token
key = ""
with open("C:/dev/discord-wmm-key.txt", 'r') as fob:
    key = fob.readline()
bot.run(key)