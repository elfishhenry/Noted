import discord
from discord.ext import commands
import ezcord
from cryptography.fernet import Fernet
import os # For checking file existence

class NotesDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("notes.db")
        self._fernet_instance = None

    async def _get_fernet(self):
        if self._fernet_instance is None:
            key_file = "secret.key"
            if not os.path.exists(key_file):
                # Consider generating a key if it doesn't exist or raising a more specific error.
                # For now, we'll raise an error to make the missing key explicit.
                raise FileNotFoundError(
                    f"Encryption key file '{key_file}' not found. Please create it."
                )
            with open(key_file, "rb") as f:
                key = f.read()
            self._fernet_instance = Fernet(key)
        return self._fernet_instance

    async def setup(self):
        await self.exec(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )

    async def add_note(self, user_id, title, content):
        fernet = await self._get_fernet()
        encrypted_content = fernet.encrypt(content.encode()).decode() # Store as string
        async with self.start() as cursor:
            await cursor.exec(
                "INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)", (user_id, title, encrypted_content)
            )

    async def get_notes(self, user_id):
        fernet = await self._get_fernet()
        # Use self.all() as per the ezcord example for fetching all results
        notes_data = await self.all("SELECT id, title, content FROM notes WHERE user_id = ? ORDER BY id ASC", (user_id,))
        # Decrypt content before returning
        return [
            (nid, title, fernet.decrypt(encrypted_content.encode()).decode())
            for nid, title, encrypted_content in notes_data
        ]

    async def delete_note(self, user_id, note_id):
        # No encryption involved in delete, but _get_fernet() could be called if other setup is needed
        async with self.start() as cursor:
            await cursor.exec(
                "DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
            )
    async def edit_note(self, user_id, note_id, new_content):
        fernet = await self._get_fernet()
        encrypted_new_content = fernet.encrypt(new_content.encode()).decode()
        async with self.start() as cursor:
            await cursor.exec(
                "UPDATE notes SET content = ? WHERE id = ? AND user_id = ?", (encrypted_new_content, note_id, user_id)
            )


db = NotesDB()


class Notes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(db.setup())

    @commands.slash_command(name="addnote", description="Add a note with a title.")
    async def addnote(self, ctx: discord.ApplicationContext, title: str, content: str):
        await db.add_note(ctx.author.id, title, content)
        await ctx.respond("Note added!", ephemeral=True)

    @commands.slash_command(name="deletenote", description="Delete a note by its ID.")
    async def deletenote(self, ctx: discord.ApplicationContext, note_id: int):
        await db.delete_note(ctx.author.id, note_id)
        await ctx.respond(f"Deleted note #{note_id} if it existed.", ephemeral=True)

    @commands.slash_command(name="editnote", description="Edit a note by its ID.")
    async def editnote(self, ctx: discord.ApplicationContext, note_id: int, new_content: str):
        await db.edit_note(ctx.author.id, note_id, new_content)
        await ctx.respond(f"Edited note #{note_id} if it existed.", ephemeral=True)

    @commands.slash_command(name="notes", description="View your notes.")
    async def notes(self, ctx: discord.ApplicationContext):
        notes = await db.get_notes(ctx.author.id)
        if not notes:
            embed = discord.Embed(
                title="Your Notes",
                description="You have no notes stored yet. Use `/addnote` to create one!",
                color=discord.Color.blue()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Notes",
            color=discord.Color.green()
        )
        
        for nid, title, content in notes:
            # Truncate content if it's too long for an embed field value
            display_content = (content[:1020] + "...") if len(content) > 1024 else content
            embed.add_field(name=f"ID #{nid}: {title}", value=f"```{display_content}```", inline=False)
            if len(embed.fields) >= 25: # Discord embed field limit
                embed.set_footer(text="Showing first 25 notes. More notes exist.")
                break
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(Notes(bot))
