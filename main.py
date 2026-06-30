import discord
import os
import datetime
from discord.ext import commands
import config
import database as db
import views

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
active_recordings = {}

@bot.event
async def on_ready():
    db.init_db()
    print(f"🔥 Бот {bot.user.name} успешно запущен на раздельной структуре!")

# --- ЛОГИ WICK BOT ---
async def send_wick_log(embed):
    channel = bot.get_channel(config.WICK_LOGS_CHANNEL_ID)
    if channel: await channel.send(embed=embed)

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot: return
    embed = discord.Embed(title="🗑 Сообщение Удалено", color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Автор:", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Канал:", value=message.channel.mention, inline=True)
    embed.add_field(name="Содержимое:", value=f"```\n{message.content or 'Вложение/Эмбед'}\n```", inline=False)
    await send_wick_log(embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    if before.author.bot or before.content == after.content: return
    embed = discord.Embed(title="📝 Сообщение Изменено", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Автор:", value=f"{before.author.mention}", inline=True)
    embed.add_field(name="Канал:", value=before.channel.mention, inline=True)
    embed.add_field(name="Было:", value=f"```\n{before.content}\n```", inline=False)
    embed.add_field(name="Стало:", value=f"```\n{after.content}\n```", inline=False)
    await send_wick_log(embed)

@bot.event
async def on_member_join(member: discord.Member):
    embed = discord.Embed(title="📥 Участник зашел", color=discord.Color.green(), timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Пользователь:", value=f"{member.mention} ({member})", inline=False)
    embed.add_field(name="Регистрация:", value=f"{member.created_at.strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
    await send_wick_log(embed)

@bot.event
async def on_member_remove(member: discord.Member):
    embed = discord.Embed(title="📤 Участник вышел", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
    embed.add_field(name="Пользователь:", value=f"{member.mention} ({member})", inline=False)
    await send_wick_log(embed)

# --- КОМАНДЫ ---
@bot.command(name="отзыв")
async def cmd_review(ctx):
    view = discord.ui.View()
    button = discord.ui.Button(label="Заполнить анкету", style=discord.ButtonStyle.primary)
    async def button_callback(interaction: discord.Interaction):
        await interaction.response.send_modal(views.ReviewModal())
    button.callback = button_callback
    view.add_item(button)
    await ctx.send("📝 Нажмите кнопку ниже, чтобы открыть анкету для отзыва:", view=view)

@bot.command(name="модерация")
async def cmd_moderate(ctx):
    if not views.is_admin(ctx.author): return await ctx.send("⛔ Нет прав роли.")
    pending = db.get_next_pending()
    if not pending: return await ctx.send("🎉 Новых отзывов нет!")
    rev_id, username, admin_name, stars, text = pending
    embed = discord.Embed(title="🧐 Модерация нового отзыва", color=discord.Color.blue())
    embed.add_field(name="Ник Игрока", value=username).add_field(name="Ник Админа", value=admin_name).add_field(name="Оценка", value=f"{stars}/10")
    embed.add_field(name="Текст", value=text, inline=False)
    await ctx.send(embed=embed, view=views.ModerationView(rev_id, bot))

@bot.command(name="снять")
async def cmd_remove(ctx, member: discord.Member = None, *, причина: str = "Не указана"):
    if not views.is_admin(ctx.author): return await ctx.send("⛔ Нет прав роли.")
    if member is None: return await ctx.send("❌ Укажите пользователя: `!снять @User Нарушение`")
    try: await ctx.message.delete()
    except: pass
    await ctx.send(f"⚙️ **Панель управления наказанием** для {member.mention}\n📝 **Причина:** {причина}", view=views.PunishmentView(member, причина))

@bot.command(name="эмбед")
async def cmd_embed(ctx):
    if not views.is_admin(ctx.author): return await ctx.send("⛔ Доступно только администрации.")
    builder = views.EmbedBuilderView(ctx.channel)
    await ctx.send("🛠 **Временное меню конструктора эмбеда**", embed=builder.embed, view=builder)

# --- СИСТЕМА КРЕЙГА ---
class AudioSink(discord.sinks.WaveSink):
    pass

@bot.command(name="запись_старт")
async def cmd_record_start(ctx):
    if not views.is_admin(ctx.author): return await ctx.send("⛔ Доступ запрещен.")
    if not ctx.author.voice: return await ctx.send("❌ Вы должны находиться в голосовом канале!")
    vc = await ctx.author.voice.channel.connect()
    active_recordings[ctx.guild.id] = vc
    vc.start_recording(AudioSink(), record_finished, ctx.channel)
    await ctx.send("🔴 **Запись голоса началась!** Используйте `!запись_стоп` для завершения.")

async def record_finished(sink: discord.sinks.Sink, channel: discord.TextChannel, *args):
    log_channel = bot.get_channel(config.AUDIO_LOGS_CHANNEL_ID) or channel
    await log_channel.send("💾 **Обработка аудиофайлов записи...**")
    for user_id, audio_file in sink.audio_data.items():
        user = await bot.fetch_user(user_id)
        filename = f"record_{user_id}.wav"
        with open(filename, "wb") as f:
            f.write(audio_file.file.getvalue())
        await log_channel.send(content=f"🎤 Лог голоса: {user.mention}", file=discord.File(filename))
        os.remove(filename)

@bot.command(name="запись_стоп")
async def cmd_record_stop(ctx):
    if not views.is_admin(ctx.author): return
    if ctx.guild.id not in active_recordings: return await ctx.send("❌ Запись не ведется.")
    vc = active_recordings.pop(ctx.guild.id)
    vc.stop_recording()
    await vc.disconnect()
    await ctx.send("🛑 Запись остановлена, аудио выгружается.")

if __name__ == "__main__":
    bot.run(config.TOKEN)
