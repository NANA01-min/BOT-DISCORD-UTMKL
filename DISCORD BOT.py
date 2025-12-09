import discord
from discord.ext import commands
from discord import ui
import os
import re
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Check if token was loaded
if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in .env file!")
    exit(1)

# --- Configuration Variables ---
# --- REVERTED TO GENERIC PLACEHOLDERS ---
UNVERIFIED_ROLE_NAME = 'Unverified'
VERIFIED_ROLE_NAME = 'Konco-konco UTMKL ESPORTSr'
# ----------------------------------------

INTRODUCTION_CHANNEL_NAME = 'introductions'
FORMAT_CHANNEL_NAME = 'format-template'
# CHANGED: Name of the channel where the public welcome message appears
WELCOME_CHANNEL_NAME = 'welcome'

# The exact text people should copy and paste
COPYABLE_FORMAT = """
Name: 
Age :
Favourite Game RN:
Experience: 
Hope:
Fun fact:
"""
REQUIRED_KEYWORDS = ["Name:", "Age :", "Favourite Game RN:", "Experience:", "Hope:", "Fun fact:"]
MIN_TOTAL_LENGTH = 50

FORMAT_PATTERN = re.compile(
    r"Name:.*" + r".*Age :.*" + r".*Favourite Game RN:.*" + r".*Experience:.*" + r".*Hope:.*" + r".*Fun fact:.*",
    re.DOTALL | re.IGNORECASE
)

passed_intro_format = {}

# --- Bot Setup ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


# Define the View which contains the button logic
class VerifyButtonView(ui.View):
    def __init__(self, author_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.guild_id = guild_id

    @ui.button(label="Verify Now", style=discord.ButtonStyle.green, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != self.author_id:
            await interaction.followup.send("This button is not for you.", ephemeral=True)
            return

        guild = bot.get_guild(self.guild_id)
        member = guild.get_member(interaction.user.id)
        if not member: await interaction.followup.send("Could not find you in the server.", ephemeral=True); return

        unverified_role = discord.utils.get(guild.roles, name=UNVERIFIED_ROLE_NAME)
        verified_role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)

        if unverified_role in member.roles and verified_role:
            await member.add_roles(verified_role)
            await member.remove_roles(unverified_role)
            if member.id in passed_intro_format: del passed_intro_format[member.id]
            for child in self.children: child.disabled = True
            await interaction.message.edit(view=self)
            await interaction.followup.send("Verification complete! Welcome to the server.", ephemeral=True)
            print(f'{member.name} has been fully verified via button press in DM.')

            welcome_channel = discord.utils.get(guild.channels, name=WELCOME_CHANNEL_NAME)
            if welcome_channel:
                member_count = guild.member_count
                await welcome_channel.send(f"🎉 **{member.mention}** just verified and joined the main chat! They are our **#{member_count}** member!")
        else:
            await interaction.followup.send("An error occurred during verification (check roles/hierarchy).", ephemeral=True)


@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user}')
    print(f'Bot ID: {bot.user.id}')
    await bot.change_presence(status=discord.Status.invisible)
    print(f'Bot status set to Invisible.')


@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! {round(bot.latency * 1000)}ms')


@bot.command()
@commands.has_permissions(administrator=True)
async def send_format_template(ctx):
    if not ctx.guild: return
    format_channel = discord.utils.get(ctx.guild.channels, name=FORMAT_CHANNEL_NAME)
    if format_channel:
        try:
            await format_channel.send(f"**👇 COPY AND PASTE THE TEXT BELOW INTO `#{INTRODUCTION_CHANNEL_NAME}` 👇**")
            await format_channel.send(f"```\n{COPYABLE_FORMAT.strip()}\n```")
            await ctx.send(f"Template messages posted in `#{FORMAT_CHANNEL_NAME}`.")
        except discord.Forbidden:
            await ctx.send(f"Error: No permission in `#{FORMAT_CHANNEL_NAME}`.")
    else: await ctx.send(f"Error: Channel `#{FORMAT_CHANNEL_NAME}` not found.")
    try: await ctx.message.delete()
    except discord.Forbidden: pass

@bot.command()
@commands.has_permissions(administrator=True)
async def verify_user(ctx, member: discord.Member):
    unverified_role = discord.utils.get(ctx.guild.roles, name=UNVERIFIED_ROLE_NAME)
    verified_role = discord.utils.get(ctx.guild.roles, name=VERIFIED_ROLE_NAME)
    if unverified_role in member.roles:
        await member.add_roles(verified_role)
        await member.remove_roles(unverified_role)
        await ctx.send(f"Manually verified {member.mention}.")
        welcome_channel = discord.utils.get(ctx.guild.channels, name=WELCOME_CHANNEL_NAME)
        if welcome_channel:
            member_count = ctx.guild.member_count
            await welcome_channel.send(f"🎉 **{member.mention}** has been manually verified! They are member **#{member_count}**.")
    else: await ctx.send(f"{member.mention} is already verified or does not have the unverified role.")


@bot.command()
@commands.has_permissions(administrator=True)
async def remind_unverified(ctx):
    if not ctx.guild: return
    unverified_role = discord.utils.get(ctx.guild.roles, name=UNVERIFIED_ROLE_NAME)
    if not unverified_role: await ctx.send(f"Error: Role named '{UNVERIFIED_ROLE_NAME}' not found."); return
    reminded_count = 0
    for member in ctx.guild.members:
        if unverified_role in member.roles and not member.bot:
            try:
                await member.send(f"Hi {member.name}, you are still unverified!\n\nPlease complete the steps to gain full access:\n1. Go to the `#{FORMAT_CHANNEL_NAME}` channel and **copy the template**.\n2. Paste and fill out your introduction in the `#{INTRODUCTION_CHANNEL_NAME}` channel.\n3. The bot will send you a **private message with a button** to verify once your format is accepted.")
                reminded_count += 1
            except discord.Forbidden: pass
    await ctx.send(f"Sent verification reminders to **{reminded_count}** unverified members.")
    try: await ctx.message.delete()
    except discord.Forbidden: pass


@bot.event
async def on_member_join(member):
    unverified_role = discord.utils.get(member.guild.roles, name=UNVERIFIED_ROLE_NAME)
    if member == bot.user: return
    if unverified_role:
        await member.add_roles(unverified_role)
        try:
            await member.send(f"Welcome! Please read the instructions below to verify.\n\n1. Go to the `#{FORMAT_CHANNEL_NAME}` channel and **long-press to copy the template**.\n2. Paste and fill out your introduction in the `#{INTRODUCTION_CHANNEL_NAME}` channel.\n3. The bot will send you a **private message with a button** to verify once your format is accepted.")
        except discord.Forbidden: pass


@bot.event
async def on_message(message):
    if message.author == bot.user or message.content.strip().startswith('!'):
        await bot.process_commands(message)
        return
    if message.channel.name == INTRODUCTION_CHANNEL_NAME:
        author_id = message.author.id
        content = message.content.strip()
        format_matches = bool(FORMAT_PATTERN.match(content))
        is_long_enough = len(content) >= MIN_TOTAL_LENGTH
        if format_matches and is_long_enough:
            if author_id not in passed_intro_format:
                passed_intro_format[author_id] = True
                view = VerifyButtonView(author_id, message.guild.id)
                try:
                    await message.author.send(f"Your introduction format is correct! Press the button below to verify.", view=view)
                    await message.add_reaction("✅")
                except discord.Forbidden:
                    await message.channel.send(f"{message.author.mention}, I can't DM you! Please enable DMs to receive the verification button.")
        else:
            try:
                await message.delete()
                await message.author.send(f"Your message in `#{INTRODUCTION_CHANNEL_NAME}` did not follow the required format or was too short.\n\nPlease go to the `#{FORMAT_CHANNEL_NAME}` channel to copy the correct template.")
            except discord.Forbidden: pass
    await bot.process_commands(message)


bot.run(TOKEN)