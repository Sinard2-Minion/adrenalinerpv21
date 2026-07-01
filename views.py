import discord
from discord.ui import Modal, InputText
import datetime
import database as db
import config

def is_admin(member: discord.Member):
    return any(role.id == config.ADMIN_ROLE_ID for role in member.roles)

class ReviewModal(Modal):
    def __init__(self):
        super().__init__(title="Анкета на отзыв")
        
    admin_name = InputText(label="Ник Админа", placeholder="Введите ник администратора", required=True)
    stars = InputText(label="Звезды (от 0 до 10)", placeholder="Например: 10", required=True, max_length=2)
    review_text = InputText(label="Отзыв (необязательно)", style=discord.InputTextStyle.paragraph, required=False, max_length=800)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            stars_val = int(self.stars.value)
            if not (0 <= stars_val <= 10): raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Ошибка: Оценка должна быть числом от 0 до 10!", ephemeral=True)

        text_val = self.review_text.value if self.review_text.value else "Не указан"
        db.save_review(interaction.user.id, str(interaction.user), self.admin_name.value, stars_val, text_val)
        await interaction.response.send_message("✅ Ваш отзыв успешно отправлен на модерацию!", ephemeral=True)

class ModerationView(discord.ui.View):
    def __init__(self, review_id, bot):
        super().__init__(timeout=None)
        self.review_id = review_id
        self.bot = bot

    @discord.ui.button(label="✅ Одобрить", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user):
            return await interaction.response.send_message("⛔ Отказано в доступе.", ephemeral=True)

        review = db.get_review_by_id(self.review_id)
        if not review: return await interaction.response.send_message("❌ Отзыв не найден.", ephemeral=True)
            
        db.update_status(self.review_id, "approved")
        u_id, username, admin_name, stars, text = review

        channel = self.bot.get_channel(config.REVIEWS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="⭐️ НОВЫЙ ОТЗЫВ О СТАФФЕ ⭐️", color=discord.Color.gold())
            embed.add_field(name="📋 Ник Админа", value=f"```\n{admin_name}\n```", inline=False)
            embed.add_field(name="👤 Ник игрока", value=f"<@{u_id}> ({username})", inline=False)
            embed.add_field(name="✨ Звезды", value=f"**{stars}/10**", inline=False)
            embed.add_field(name="💬 Отзыв", value=f"*{text}*", inline=False)
            await channel.send(embed=embed)
            await interaction.response.edit_message(content="✅ Отзыв опубликован!", view=None, embed=None)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user): return await interaction.response.send_message("⛔ Отказано в доступе.", ephemeral=True)
        db.update_status(self.review_id, "rejected")
        await interaction.response.edit_message(content="❌ Отзыв отклонен.", view=None, embed=None)

class ActionSelect(discord.ui.Select):
    def __init__(self, target_member: discord.Member, reason: str):
        self.target_member = target_member
        self.reason = reason
        options = [
            discord.SelectOption(label="Бан", description="Забанить на сервере", emoji="🔨", value="ban"),
            discord.SelectOption(label="Кик", description="Выгнать с сервера", emoji="👢", value="kick"),
            discord.SelectOption(label="Мут", description="Таймаут на 1 час", emoji="🔇", value="timeout")
        ]
        super().__init__(placeholder="Выберите тип наказания...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): return await interaction.response.send_message("⛔ Нет прав.", ephemeral=True)
        try:
            if self.values == "ban":
                await self.target_member.ban(reason=self.reason)
                await interaction.response.edit_message(content=f"🔨 **{self.target_member}** забанен. Причина: *{self.reason}*", view=None)
            elif self.values == "kick":
                await self.target_member.kick(reason=self.reason)
                await interaction.response.edit_message(content=f"👢 **{self.target_member}** кикнут. Причина: *{self.reason}*", view=None)
            elif self.values == "timeout":
                await self.target_member.timeout(datetime.timedelta(hours=1), reason=self.reason)
                await interaction.response.edit_message(content=f"🔇 **{self.target_member}** замучен на 1 час. Причина: *{self.reason}*", view=None)
        except Exception as e:
            await interaction.response.edit_message(content=f"❌ Ошибка прав: {str(e)}", view=None)

class PunishmentView(discord.ui.View):
    def __init__(self, target_member: discord.Member, reason: str):
        super().__init__(timeout=60)
        self.add_item(ActionSelect(target_member, reason))

class EmbedEditModal(Modal):
    def __init__(self, current_embed, view_builder):
        super().__init__(title="Редактирование Эмбеда")
        self.current_embed = current_embed
        self.view_builder = view_builder
        self.embed_title.default = current_embed.title
        self.embed_desc.default = current_embed.description

    embed_title = InputText(label="Заголовок", required=True, max_length=256)
    embed_desc = InputText(label="Описание / Текст", style=discord.InputTextStyle.paragraph, required=True, max_length=2000)
    embed_color = InputText(label="Цвет (HEX код, например: #ff0000)", required=False, default="#00ff00", max_length=7)

    async def on_submit(self, interaction: discord.Interaction):
        self.current_embed.title = self.embed_title.value
        self.current_embed.description = self.embed_desc.value
        try:
            color_hex = self.embed_color.value.lstrip('#')
            self.current_embed.color = discord.Color(int(color_hex, 16))
        except:
            self.current_embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=self.current_embed, view=self.view_builder)

class EmbedBuilderView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=300)
        self.channel = channel
        self.embed = discord.Embed(title="Временный Заголовок", description="Временный text эмбеда.", color=discord.Color.green())

    @discord.ui.button(label="📝 Изменить текст/цвет", style=discord.ButtonStyle.primary)
    async def edit_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedEditModal(self.embed, self))

    @discord.ui.button(label="🚀 Отправить и удалить панель", style=discord.ButtonStyle.success)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.channel.send(embed=self.embed)
        await interaction.response.edit_message(content="✅ Эмбед успешно отправлен! Данная панель уничтожена.", embed=None, view=None)
        self.stop()

    @discord.ui.button(label="🗑 Отмена", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Создание эмбеда отменено. Панель удалена.", embed=None, view=None)
        self.stop()
