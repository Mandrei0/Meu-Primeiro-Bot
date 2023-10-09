import discord
from discord.ui import Button, View
from discord.ext import commands, tasks
from discord import ButtonStyle, InteractionType
import sqlite3
import datetime
from datetime import timezone
import asyncio
from discord.ext.commands import HelpCommand
import random

intents = discord.Intents.default()
intents.message_content = True

connection = sqlite3.connect('bot_database.db')
cursor = connection.cursor()

TOKEN = 'TOKEN AQUI'

# Criação da tabela 'allplayers'
cursor.execute('''
    CREATE TABLE IF NOT EXISTS allplayers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        overall INTEGER,
        mec INTEGER,
        dec INTEGER, 
        gak INTEGER,
        twk INTEGER,
        adp INTEGER,
        ldr INTEGER,
        price INTEGER,
        nationality TEXT,
        league TEXT,
        team TEXT,
        position TEXT,
        photo_url TEXT,
        icon TEXT
    )
''')

# Criação da tabela 'organizations'
cursor.execute('''
    CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER,
        server_id INTEGER,
        org_name TEXT NOT NULL,
        org_nick TEXT NOT NULL,
        org_img TEXT,
        org_sort TEXT DEFAULT "name",
        player_count INTEGER NOT NULL DEFAULT 0,
        cofre INTEGER NOT NULL DEFAULT 0,
        roll_count INTEGER NOT NULL DEFAULT 0,
        roll_max INTEGER NOT NULL DEFAULT 3,
        claim_count INTEGER NOT NULL DEFAULT 0,
        claim_max INTEGER NOT NULL DEFAULT 1,
        selling_tax REAL NOT NULL DEFAULT 0.4,
        selling_max REAL NOT NULL DEFAULT 1.5,
        wish_rate REAL NOT NULL DEFAULT 1.0,
        wish_max INTEGER NOT NULL DEFAULT 3,
        wish_list TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (id, server_id)  -- Define a chave primária composta
    )
''')

# Criação da tabela 'organization_players'
cursor.execute('''
    CREATE TABLE IF NOT EXISTS organization_players (
        server_id INTEGER,
        org_id INTEGER,
        player_id INTEGER,
        escalado BOOL DEFAULT FALSE,
        FOREIGN KEY (server_id) REFERENCES organizations(server_id),
        FOREIGN KEY(org_id) REFERENCES organizations(id),
        FOREIGN KEY(player_id) REFERENCES allplayers(id)
    )
''')

# Criação da tabela 'store' 
cursor.execute('''
    CREATE TABLE IF NOT EXISTS store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        cost INTEGER NOT NULL,
        level_txt TEXT NOT NULL,
        photo_url TEXT,
        code TEXT
    )
''')

#Criação da tabela 'improvements' para rastrear os níveis de vantagens
cursor.execute('''
    CREATE TABLE IF NOT EXISTS improvements (
        org_id INTEGER,
        server_id INTEGER,
        scout_level INTEGER DEFAULT 0,
        wish_level INTEGER DEFAULT 0,
        business_level INTEGER DEFAULT 0,
        claim_level INTEGER DEFAULT 0,
        FOREIGN KEY(org_id) REFERENCES organizations(id),
        FOREIGN KEY(server_id) REFERENCES organizations(server_id),
        PRIMARY KEY (org_id, server_id)  -- Define a chave primária composta

    )
''')

#VARIÁVEIS GLOBAIS e ALIASES
command_aliases_map = {
    'busca': ['pesquisa', 'b', 'p', 'search'],
    'vender': ['sell'],
    'ordenar_nome': ['sort_by_name', 'sn', 'on'],
    'ordenar_país': ['sort_by_country', 'sc', 'op'],
    'ordenar_time': ['sort_by_team', 'st', 'ot'],
    'ordenar_role': ['sort_by_role', 'sr', 'or'],
    'ordenar_liga':['sort_by_league', 'sl', 'ol'],
    'roll': ['r']
}

PARAMETER_ALIASES = {
    'name': ['nome', 'n'],
    'nationality': ['country','c','nacionalidade', 'na','pais','país'],
    'team': ['time', 't'],
    'position': ['posição', 'posicao', 'p', 'r', 'role'],
    'league' : ['liga','l','region']
}

bot_name = "League Bot"
bot_photo_url = "https://img.freepik.com/fotos-gratis/imagem-aproximada-da-cabeca-de-um-lindo-leao_181624-35855.jpg?w=2000"

#CLASSES
class OrgView(discord.ui.View):
    def __init__(self, players_data, org_photo_url, org_name, org_nick, org_sort, owner_name, player_count, org_money):
        super().__init__()
        self.players_data = players_data
        self.current_page = 0
        self.org_photo_url = org_photo_url
        self.org_name = org_name
        self.org_nick = org_nick
        self.org_sort = org_sort
        self.owner_name = owner_name
        self.player_count = player_count
        self.org_money = org_money

    async def create_embed(self, page):
        players_per_page = 6
        start_idx = page * players_per_page
        end_idx = start_idx + players_per_page
        players_chunk = self.players_data[start_idx:end_idx]

        player_list = []
        for player_data in players_chunk:
            icon = get_icon(player_data['name'])
            player_name = player_data['name'].upper()
            player_overall = player_data['overall']
            player_team = player_data['team'].upper()
            player_role = player_data['position']
            
            if player_role == 'Top':
                emoji_role = '<:TOP:1142918355934785596>' 
            elif player_role == 'Jungle':
                emoji_role = '<:JUNGLE:1142918358694633572>'
            elif player_role == 'Mid':
                emoji_role = '<:MID:1142918354689065082>'
            elif player_role == 'Adc':
                emoji_role = '<:ADC:1142918351945998377>'
            else:
                emoji_role = '<:SUP:1142918350863867944>'

            player_entry = f"**{player_name}** - {icon} \n {player_overall} | {player_team} |  {emoji_role} \n"
            player_list.append(player_entry)

        player_list_text = "\n".join(player_list)

        embed = discord.Embed(title=f"[{self.org_nick}] {self.org_name}", color=discord.Color.from_rgb(134, 144,203))
        embed.set_thumbnail(url=self.org_photo_url)

        embed.add_field(name="**Dono **", value=self.owner_name.display_name, inline=False)
        embed.add_field(name="**Dinheiro **", value=self.org_money, inline=False)
        embed.add_field(name="**Número de Jogadores: **", value=str(self.player_count), inline=False)
        embed.add_field(name="**Lineup Atual**", value="A definir", inline=False)
        embed.add_field(name="**JOGADORES NO ELENCO** - Fator " + self.org_sort.capitalize(), value=player_list_text, inline=False)

        max_page = (len(self.players_data) - 1) // players_per_page
        footer_text = f"Página {page + 1}/{max_page + 1}"
        embed.set_footer(text=footer_text)

        return embed

    async def show_page(self, page):
        embed = await self.create_embed(page)
        await self.message.edit(embed=embed)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.ctx.author and interaction.message == self.message:
            return True
        await interaction.response.send_message("Este não é o botão certo para você.", ephemeral=True)
        return False

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.show_page(self.current_page)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        players_per_page = 6
        max_page = (len(self.players_data) - 1) // players_per_page
        if self.current_page < max_page:
            self.current_page += 1
            await self.show_page(self.current_page)

    async def start(self, ctx):
        self.ctx = ctx
        embed = await self.create_embed(self.current_page)
        self.message = await ctx.send(embed=embed, view=self, reference=ctx.message)

class PaginatedView(discord.ui.View):
    def __init__(self, item_names, page=0, sort_parameter=None):
        super().__init__()
        self.item_names = item_names
        self.current_page = page
        self.sort_parameter = sort_parameter

    def create_embed(self):
        items_per_page = 20
        start_idx = self.current_page * items_per_page
        end_idx = start_idx + items_per_page
        item_list = "\n".join(self.item_names[start_idx:end_idx])
        
        embed = discord.Embed(color=discord.Color.from_rgb(38, 249,255))
        embed.description = item_list
        
        total_pages = (len(self.item_names) + items_per_page - 1) // items_per_page
        embed.set_footer(text=f"Página {self.current_page + 1} de {total_pages}")

        if self.sort_parameter:
            embed.title = f"Ordenado por {self.sort_parameter.capitalize()}"

        return embed

    @discord.ui.button(emoji="⬅️")
    async def previous_page(self, button, interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed())

    @discord.ui.button(emoji="➡️")
    async def next_page(self, button, interaction):
        items_per_page = 20
        max_page = (len(self.item_names) + items_per_page - 1) // items_per_page

        if self.current_page < max_page:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed())

class SortedPaginatedView(PaginatedView):
    def __init__(self, data, sort_parameter, org_sort):
        super().__init__(data)
        self.sort_parameter = sort_parameter
        self.org_sort = org_sort

    def create_embed(self):
        embed = super().create_embed()
        embed.set_footer(text=f'Sorted by: {self.sort_parameter} | Current Sort: {self.org_sort}')
        return embed

def get_sorted_paginated_view(sorted_data, sort_parameter):
    sorted_data_string = "\n".join(sorted_data)  # Adjust formatting as needed
    paginated_view = PaginatedView(sorted_data_string.split('\n'), sort_parameter=sort_parameter)
    embed = paginated_view.create_embed()
    return embed, paginated_view

class SearchResultsView(discord.ui.View):
    def __init__(self, search_results, search_params):
        super().__init__()
        self.search_results = search_results
        self.search_params = search_params  # Armazene os parâmetros de pesquisa
        self.current_page = 0
        self.results_per_page = 10

    async def create_embed(self, page):
        start_idx = page * self.results_per_page
        end_idx = start_idx + self.results_per_page
        results = self.search_results[start_idx:end_idx]

        embed = discord.Embed(
            title="Resultados da Pesquisa",
            color=discord.Color.from_rgb(38, 249,255)
        )
        embed.set_footer(text=f"Página {page + 1}/{(len(self.search_results) + self.results_per_page - 1) // self.results_per_page}")

        search_params_str = "\n".join([f"{param}: {value}" for param, value in self.search_params.items()])
        embed.add_field(name="Parâmetros de Pesquisa", value=search_params_str, inline=False)

        for player_name, overall in results:
            dono = await get_owner(self.ctx, player_name)
            icon = get_icon(player_name)  
            embed.add_field(name=f"{player_name}{icon} - {overall}", value=f"Dono: {dono}", inline=False)

        return embed

    async def show_page(self, page):
        embed = await self.create_embed(page)
        await self.message.edit(embed=embed)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.ctx.author and interaction.message == self.message:
            return True
        await interaction.response.send_message("Este não é o botão certo para você.", ephemeral=True)
        return False

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.show_page(self.current_page)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        max_page = (len(self.search_results) + self.results_per_page - 1) // self.results_per_page - 1
        if self.current_page < max_page:
            self.current_page += 1
            await self.show_page(self.current_page)

    async def start(self, ctx):
        self.ctx = ctx
        embed = await self.create_embed(self.current_page)
        self.message = await ctx.send(embed=embed, view=self, reference=ctx.message)
 
class PlayerInfoView(discord.ui.View):
    def __init__(self, ctx, players):
        super().__init__()
        self.ctx = ctx
        self.players = players
        self.current_page = 0
        self.message = None

    async def show(self):
        await self.update_page()

    async def update_page(self):
        player = self.players[self.current_page]
        owner_name = await get_owner(self.ctx, player)
        name, nationality, team, position, league, photo_url, icon, price = get_player_details(player)
        name = name.upper()
        nationality = nationality.upper()
        team = team.upper()
        position = position.upper()
        league = league.upper()

        embed = discord.Embed(
            title=f'Jogador: {name}',
            color=discord.Color.from_rgb(38, 249,255)
        )

        embed.add_field(name='Nacionalidade', value=nationality, inline=False)
        embed.add_field(name='Liga', value=league, inline=False)
        embed.add_field(name='Time', value=team, inline=False)
        embed.add_field(name='Posição', value=position, inline=False)
        embed.add_field(name='Preço', value=price, inline=False)
        embed.add_field(name='Dono', value=owner_name, inline=False)
        embed.set_image(url=photo_url)
        embed.set_author(name=bot_name, icon_url=bot_photo_url)
        embed.set_footer(text=f'Página {self.current_page + 1}/{len(self.players)}')

        if self.message is None:
            self.message = await self.ctx.send(embed=embed, view=self, reference=self.ctx.message)
        else:
            await self.message.edit(embed=embed)

    @discord.ui.button(emoji="⬅️")
    async def previous_page(self, button, interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page()

    @discord.ui.button(emoji="➡️")
    async def next_page(self, button, interaction):
        if self.current_page < len(self.players) - 1:
            self.current_page += 1
            await self.update_page()

class PlayerNotFoundError(commands.CommandError):
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value
        super().__init__(f"Player not found with {parameter} equal to '{value}'")

class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()

    async def send_bot_help(self, mapping):
        try:
            categories = {
                "Organização e Usuário": ['registrar', 'nome', 'sigla', 'imagem', 'org', 'detalhes'],
                "Transações": ['roll','vender', 'negociar'],
                "Busca e Informação": ['busca', 'info'],
                "Ordenação": ['ordenar_nome', 'ordenar_país', 'ordenar_liga', 'ordenar_time', 'ordenar_role', 'ordenar_overall'],
                "Loja": ['loja', 'epico', 'lendario', 'mitico', 'ultimate'],
                "Lista de Interesses": ["interesses", "scout", "remover"],
            }

            for category, command_names in categories.items():
                embed = discord.Embed(title=f"**{category.upper()}**", description="", color=discord.Color.from_rgb(255, 0,255))
                for i, command_name in enumerate(command_names):
                    command = self.context.bot.get_command(command_name.upper())
                    if command and not command.hidden:
                        command_info = f"**Descrição:** {command.brief}\n"
                        if command.aliases:
                            command_info += f"**Pseudônimos:** {', '.join(command.aliases)}\n"
                        if command.usage:
                            command_info += f"**Uso:** {command.usage}\n"
                        embed.add_field(name=f"{command.name.upper()}", value=command_info, inline=False)
                        if i < len(command_names) - 1:
                            embed.add_field(name="", value="\u200b", inline=False)

                if embed.fields:
                    await self.context.author.send(embed=embed)
                    
        except Exception as e:
            print("An error occurred while sending the help embeds:", e)

bot = commands.Bot(command_prefix='!', intents=intents, help_command=CustomHelpCommand(), case_insensitive=True)

class TopPlayersView(discord.ui.View):
    def __init__(self, top_players_data):
        super().__init__()
        self.top_players_data = top_players_data
        self.current_page = 0
        self.results_per_page = 10

    async def create_embed(self, page):
        start_idx = page * self.results_per_page
        end_idx = start_idx + self.results_per_page
        results = self.top_players_data[start_idx:end_idx]

        embed = discord.Embed(
            title="Top Jogadores por Overall",
            color=discord.Color.gold()
        )

        for rank, (name, overall) in enumerate(results, start=start_idx + 1):
            embed.add_field(name=f"{rank}. {name}", value=f"Overall: {overall}", inline=False)

        max_page = (len(self.top_players_data) + self.results_per_page - 1) // self.results_per_page - 1
        embed.set_footer(text=f"Página {page + 1}/{max_page + 1}")

        return embed

    async def show_page(self, page):
        embed = await self.create_embed(page)
        await self.message.edit(embed=embed)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.ctx.author and interaction.message == self.message:
            return True
        await interaction.response.send_message("Este não é o botão certo para você.", ephemeral=True)
        return False

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.show_page(self.current_page)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        max_page = (len(self.top_players_data) + self.results_per_page - 1) // self.results_per_page - 1
        if self.current_page < max_page:
            self.current_page += 1
            await self.show_page(self.current_page)

    async def start(self, ctx):
        self.ctx = ctx
        embed = await self.create_embed(self.current_page)
        self.message = await ctx.send(embed=embed, view=self)






#FUNÇÕES

# Função para remover um jogador do banco de dados
def remove_player(ctx, name):
    cursor.execute('SELECT id FROM allplayers WHERE name = ?', (name,))
    player = cursor.fetchone()
    if not player:
        return False

    player_id = player[0]

    remove_from_elenco(ctx, player_id)

    cursor.execute('DELETE FROM allplayers WHERE id = ?', (player_id,))
    connection.commit()
    return True

# Função para remover um jogador de todas as organizações em que ele está presente
def remove_from_elenco(ctx, player_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT org_id FROM organization_players WHERE player_id = ? AND server_id = ?', (player_id, server_id))
    org_ids = cursor.fetchall()

    for org_id in org_ids:
        # Remover o jogador da organização
        cursor.execute('DELETE FROM organization_players WHERE org_id = ? AND player_id = ?', (org_id[0], player_id))
        connection.commit()
        
        cursor.execute('UPDATE organizations SET player_count = player_count - 1 WHERE id = ? AND server_id = ?', (org_id[0], server_id))
        connection.commit()

# Função para obter um jogador aleatório com base na raridade
def get_random_player(ctx, discord_id):
    server_id = ctx.guild.id  
    try:
        cursor.execute('SELECT wish_rate, wish_list FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
        result = cursor.fetchone()

        if result:
            wish_rate, wish_list = result[0], result[1]
            wish_list_ids = [int(id_str) for id_str in wish_list.split(',')] if wish_list else []

        cursor.execute('SELECT COUNT(*) FROM allplayers')
        pool_size = cursor.fetchone()[0]
        chance = wish_rate / pool_size

        # Gerar um número aleatório entre 0 e 100 para determinar a raridade
        random_number = random.randint(1, 100)

        # Determinar a raridade com base no número aleatório gerado
        if random_number <= 30:
            overall_range = (0, 57)  # 30% de chance para overall entre 0 e 57
        elif random_number <= 55:
            overall_range = (58, 65)  # 25% de chance para overall entre 58 e 65
        elif random_number <= 75:
            overall_range = (66, 73)  # 20% de chance para overall entre 66 e 73
        elif random_number <= 90:
            overall_range = (74, 81)  # 15% de chance para overall entre 74 e 81
        elif random_number <= 95:
            overall_range = (82, 89)  # 5% de chance para overall entre 82 e 89
        elif random_number <= 99:
            overall_range = (90, 94)  # 4% de chance para overall entre 90 e 94
        else:
            overall_range = (95, 99)  # 1% de chance para overall entre 95 e 99

        if random.random() < chance:
            if wish_list_ids:
                # Criar uma string de placeholders para a Lista de Desejos
                placeholders = ', '.join(['?'] * len(wish_list_ids))

                # Montar a consulta SQL com placeholders
                query = f'SELECT id FROM allplayers WHERE id IN ({placeholders}) AND overall >= ? AND overall <= ?'

                # Montar os argumentos para a consulta
                args = wish_list_ids + [overall_range[0], overall_range[1]]

                # Executar a consulta com os argumentos
                cursor.execute(query, args)
                wishlist_players = cursor.fetchall()

                if wishlist_players:
                    # Se houver jogadores na Lista de Desejos no mesmo overall_range, escolha aleatoriamente um deles com base no wish_rate
                    return random.choice(wishlist_players)[0]

        # Consulta SQL para obter um jogador aleatório dentro da faixa de overall determinada
        cursor.execute('SELECT id FROM allplayers WHERE overall >= ? AND overall <= ? ORDER BY RANDOM() LIMIT 1', overall_range)
        player = cursor.fetchone()

        if player:
            return player[0]

    except Exception as e:
        print(f"Ocorreu um erro ao buscar um jogador aleatório: {str(e)}")

    return None

def get_organization(ctx, discord_id):
    server_id = ctx.guild.id
    cursor.execute('SELECT id FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

# Função para obter a organização do usuário
def get_organization_players(ctx, org_id):
    server_id = ctx.guild.id 
    cursor.execute('SELECT player_id FROM organization_players WHERE org_id = ? AND server_id = ? ', (org_id, server_id))
    result = cursor.fetchall()
    player_ids = [row[0] for row in result]
    return player_ids

# Função para buscar um usuário pelo seu nome, nacionalidade, time ou posição
def search_players(search_params):
    query = "SELECT name, overall FROM allplayers WHERE "
    values = []

    for param, value in search_params.items():
        real_param = None
        for param_name, aliases in PARAMETER_ALIASES.items():
            if param.lower() == param_name or param.lower() in aliases:
                real_param = param_name
                break

        if real_param is not None:
            query += f"{real_param} LIKE ? AND "
            values.append('%' + value.lower() + '%')

    # Remove o último "AND" da consulta
    query = query[:-5]

    query += "ORDER BY overall DESC"  # Ordena por overall em ordem decrescente

    cursor.execute(query, tuple(values))
    players = cursor.fetchall()
    return players

# Função para remover um jogador do elenco do usuário e receber um valor pela venda
def venderFunc(ctx, discord_id, player_name, valor_recebido):
    org_id = discord_id
    player_name = player_name.lower()
    server_id = ctx.guild.id
    cursor.execute('SELECT id FROM allplayers WHERE name = ?', (player_name,))
    player_id = cursor.fetchone()

    # Remove a associação da carta da organização do usuário no servidor atual
    cursor.execute('DELETE FROM organization_players WHERE server_id = ? AND org_id = ? AND player_id = ?', (server_id, org_id, player_id[0]))
    connection.commit()

    cursor.execute('UPDATE organizations SET player_count = player_count - 1 WHERE id = ? AND server_id = ?', (org_id, server_id))
    connection.commit()

    # Adicionar o valor recebido ao saldo do usuário
    cursor.execute('UPDATE organizations SET cofre = cofre + ? WHERE id = ? AND server_id = ?', (valor_recebido, discord_id, server_id))
    connection.commit()

    return True

# Função para buscar informações detalhadas de um jogador pelo nome
def get_player_details(player_name):
    cursor.execute('SELECT name, nationality, team, position, league, photo_url, icon, price FROM allplayers WHERE name = ?', (player_name,))
    player_details = cursor.fetchone()
    return player_details

# Função para buscar a URL da foto da carta de um jogador pelo nome
def get_player_photo_url(player_name):
    cursor.execute('SELECT photo_url FROM allplayers WHERE name = ?', (player_name,))
    photo_url = cursor.fetchone()
    if photo_url is not None:
        return photo_url[0]
    return None

# Função para buscar informações detalhadas de um jogador pelo id
def get_player_details_by_id(player_id):
    cursor.execute('SELECT name, nationality, team, position, league, photo_url, icon, price FROM allplayers WHERE id = ?', (player_id,))
    player_details = cursor.fetchone()
    return player_details

# Função para obter o nome da org de um player
def get_org_name(ctx, discord_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT org_name FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

# Função para atualizar o nome da organização no banco de dados
def update_org_name(ctx, discord_id, new_org_name):
    server_id = ctx.guild.id  
    cursor.execute('UPDATE organizations SET org_name = ? WHERE id = ? AND server_id = ?', (new_org_name, discord_id, server_id))
    connection.commit()

# Função para obter o apelido da org de um player
def get_org_nick(ctx, discord_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT org_nick FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

# Função para atualizar o nick da organização no banco de dados
def update_org_nick(ctx, discord_id, new_org_nick):
    server_id = ctx.guild.id  
    cursor.execute('UPDATE organizations SET org_nick = ? WHERE id = ? AND server_id = ?', (new_org_nick, str(discord_id), server_id))
    connection.commit()

def get_org_img(ctx, discord_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT org_img FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    return

def update_org_img(ctx, discord_id, new_org_img):
    server_id = ctx.guild.id  
    cursor.execute('UPDATE organizations SET org_img = ? WHERE id = ? AND server_id = ?', (new_org_img, str(discord_id), server_id))
    connection.commit()

def get_org_money(ctx, discord_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT cofre FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    return result[0]

# Função para ordenar a organização do usuário
def get_sorted_organization(ctx, discord_id, order_by=None):
    server_id = ctx.guild.id  
    query = get_sorted_organization_query(discord_id, server_id, order_by=order_by)
    cursor.execute(query, (discord_id, server_id))
    result = cursor.fetchall()
    return result

def get_sorted_organization_query(discord_id, server_id, order_by=None):
    valid_columns = ['name', 'nationality', 'position', 'team', 'overall', 'league']
    
    if order_by and order_by not in valid_columns:
        return f'SELECT * FROM organization_players WHERE org_id = ? AND server_id = ?'
    
    position_order = {
        'Top': 1,
        'Jungle': 2,
        'Mid': 3,
        'Adc': 4,
        'Sup': 5
    }
    
    base_query = f'SELECT allplayers.name, allplayers.overall, allplayers.nationality, allplayers.team, allplayers.position, allplayers.league FROM allplayers JOIN organization_players ON allplayers.id = organization_players.player_id WHERE organization_players.org_id = ? AND organization_players.server_id = ?'
    
    if order_by:
        if order_by == 'position':
            query = f'{base_query} ORDER BY CASE allplayers.position ' + ' '.join([f"WHEN '{pos}' THEN {order}" for pos, order in position_order.items()]) + ' END'
        elif order_by == 'overall':
            query = f'{base_query} ORDER BY allplayers.{order_by} DESC'
        else:
            query = f'{base_query} ORDER BY allplayers.{order_by}'
    else:
        query = base_query

    return query


# Função para buscar o player_count de um usuário
def get_player_count(ctx, discord_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT player_count FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return 0

# Função para APAGAR TUDO.
def clear_databases():
    cursor.execute('DELETE FROM allplayers')
    cursor.execute('DELETE FROM organizations')
    cursor.execute('DELETE FROM organization_players')
    connection.commit()

# Função para fazer a manutenção da configuração da organização do usuário
def update_organization_sort(ctx, discord_id, org_sort):
    server_id = ctx.guild.id  
    cursor.execute('UPDATE organizations SET org_sort = ? WHERE id = ? AND server_id = ?', (org_sort, discord_id, server_id))
    connection.commit()

# Função para obter a configuração de ordenação da organização do usuário
def get_organization_sort(ctx, discord_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT org_sort FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
    result = cursor.fetchone()
    if result:
        return result[0]
    return 'name'

# Função para obter o overall de um jogador
def get_player_overall(player_id):
    query = "SELECT overall FROM allplayers WHERE id = ?"
    cursor.execute(query, (player_id,))
    result = cursor.fetchone()
    if result:
        overall = result[0]
        return overall
    return 0

# Function to increment roll_count
def increment_roll_count(ctx, org_id):
    server_id = ctx.guild.id  
    cursor.execute('UPDATE organizations SET roll_count = roll_count +1 WHERE id = ? AND server_id = ?',(org_id, server_id))
    connection.commit()

# Função para redefinir roll_count
def reset_roll_count(org_id):
    cursor.execute('UPDATE organizations SET roll_count = 0 WHERE id = ?', (org_id,))
    connection.commit()

# Função para redefinir claim_count
def reset_claim_count(org_id):
    cursor.execute('UPDATE organizations SET claim_count = 0 WHERE id = ?', (org_id,))
    connection.commit()

# Função para adicionar um jogador à organização e incrementar claim_count
async def add_player_to_organization(ctx, author_id, player_id):
    server_id = ctx.guild.id  
    if await has_claim(ctx, author_id):
        cursor.execute('INSERT INTO organization_players (org_id, server_id, player_id) VALUES (?, ?, ?)', (author_id, server_id ,player_id))
        connection.commit()

        cursor.execute('UPDATE organizations SET player_count = player_count + 1, claim_count = claim_count + 1 WHERE id = ? AND server_id = ?', (author_id, server_id))
        connection.commit()

def get_bonus(player_name):
    cursor.execute('SELECT price FROM allplayers WHERE name = ?', (player_name,))
    price = cursor.fetchone()
    bonus = price[0]* 0.15
    return bonus

# Função para verificar se um jogador pode ser adicionado à organização
async def is_player_available(ctx, player_id):
    cursor.execute('SELECT name, photo_url FROM allplayers WHERE id = ?', (player_id,))
    player_info = cursor.fetchone()

    if player_info:
        name, photourl = player_info
        name = name.upper()
        embed = discord.Embed(title=name)
        embed.set_image(url=photourl)

        server_id = ctx.guild.id  
        cursor.execute('SELECT * FROM organization_players WHERE server_id = ? AND player_id = ?', (server_id, player_id))
        player_owned = cursor.fetchone()

        if not player_owned:
            # Jogador está disponível para contratação
            embed.add_field(name="", value=f"O jogador {name} está disponível, reaja com <:confirmar:1155491221863665666> para contratá-lo!")
            embed.color = discord.Color.green()
        else:
            # Jogador não está disponível, oferece um bônus
            embed.add_field(name="", value=f"O jogador {name} não está disponível, reaja com 💰 para obter um bônus!")
            embed.color = discord.Color.red()

        message = await ctx.send(embed=embed, reference=ctx.message)

        if not player_owned:
            await message.add_reaction("<:confirmar:1155491221863665666>")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "<:confirmar:1155491221863665666>" and reaction.message.id == message.id

            try:
                reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                claim_info = get_claim_info(ctx, ctx.author.id)
                if claim_info and claim_info[0] < claim_info[1]:
                    await add_player_to_organization(ctx, ctx.author.id, player_id)
                    await ctx.send(f"Jogador adicionado ao elenco com sucesso! Agora você possui o jogador {name}.", reference=ctx.message)
                else:
                    reset_time = calculate_time_until_reset(reset_claim_count_task)
                    await ctx.send(f"Você não pode contratar esse jogador agora! Seus contratos resetam em: {reset_time}", reference=ctx.message)
            except asyncio.TimeoutError:
                pass  # Não envia nenhuma mensagem se o tempo esgotar
        else:
            await message.add_reaction("💰")
            try:
                reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=lambda reaction, user: user == ctx.author and str(reaction.emoji) == "💰" and reaction.message.id == message.id)
                bonus = get_bonus(name.lower())
                org_money = get_org_money(ctx, ctx.author.id)
                update_organization_money(ctx, ctx.author.id, org_money + bonus)
                bonus_embed = discord.Embed(description=f"Bônus Adquirido! Você recebeu {bonus} moedas e agora possui {org_money + bonus} moedas no cofre.", color=discord.Color.green())
                await ctx.send(embed=bonus_embed, reference=ctx.message)
            except asyncio.TimeoutError:
                pass  # Não envia nenhuma mensagem se o tempo esgotar
    else:
        await ctx.send("As informações do jogador não estão disponíveis no momento.", reference=ctx.message)

# Função para obter informações sobre os claims do usuário
def get_claim_info(ctx, author_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT claim_count, claim_max FROM organizations WHERE id = ? AND server_id = ?', (author_id, server_id))
    claim_info = cursor.fetchone()
    if claim_info:
        return claim_info
    else:
        return (0, 0)  # Retornar um valor padrão se não houver informações

# Função para obter informações sobre os rolls do usuário
def get_roll_info(ctx, author_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT roll_count, roll_max FROM organizations WHERE id = ? AND server_id = ?', (author_id, server_id))
    roll_info = cursor.fetchone()
    if roll_info:
        return roll_info
    else:
        return (0, 3)  # Retornar um valor padrão se não houver informações

# Função para verificar se um jogador pode adicionar um boneco à sua organização
async def has_claim(ctx, author_id):
    server_id = ctx.guild.id  
    cursor.execute('SELECT claim_count, claim_max FROM organizations WHERE id = ? AND server_id = ?', (author_id, server_id))
    claim_info = cursor.fetchone()

    if claim_info:
        claim_count, claim_max = claim_info
        return claim_count < claim_max
    else:
        return False

# Função para calcular o tempo restante até o reset de claims ou rolls
def calculate_time_until_reset(reset_task):
    time_until_reset = reset_task.next_iteration - datetime.datetime.now(datetime.timezone.utc)
    hours, remainder = divmod(time_until_reset.seconds, 3600)
    minutes = remainder // 60
    seconds = remainder % 60
    return f"{minutes} minutos e {seconds} segundos"

def get_improvements_from_database():
    cursor.execute('SELECT name, description, cost, level_txt, photo_url, code FROM store')
    improvements = cursor.fetchall()
    return improvements

# Função para criar a embed da loja
def create_store_embed(organization_name, organization_money, available_improvements, max_level_improvements):
    embed = discord.Embed(title="Loja de Aprimoramentos", description=f"Organização: {organization_name}", color=discord.Color.from_rgb(255, 0, 255))
    
    if available_improvements:
        for improvement in available_improvements:
            name, description, cost, level_txt, photo_url, _ = improvement
            field_value = f"**EFEITO:** {description}\n**Custo:** {cost} moedas"
            field_value += "\n\u200b"  # Unicode zero-width space
            embed.add_field(name=f"{photo_url} {name} {level_txt}", value=field_value, inline=False)

    if max_level_improvements:        
        for improvement in max_level_improvements:
            name, description, _, _, photo_url, _ = improvement
            field_value = f"**EFEITO:** Este aprimoramento já atingiu o nível máximo."
            field_value += "\n\u200b"  # Unicode zero-width space
            embed.add_field(name=f"{photo_url} {name} - MAX", value=field_value, inline=False)
    
    embed.set_author(name=bot_name, icon_url=bot_photo_url)
    embed.set_footer(text=f"Dinheiro da Organização: {organization_money} moedas")
    return embed

def get_improvements_info(ctx, organization_id):
    server_id = ctx.guild.id    
    cursor.execute('SELECT scout_level, wish_level, business_level, claim_level FROM improvements WHERE org_id = ? AND server_id = ?', (organization_id, server_id))
    improvement_info = cursor.fetchone()    
    return improvement_info

def update_level(ctx, organization_id, improvement_type, new_level):
    server_id = ctx.guild.id    
    update_query = f"UPDATE improvements SET {improvement_type} = ? WHERE org_id = ? and server_id = ?"
    cursor.execute(update_query, (new_level, organization_id, server_id))
    connection.commit()

def update_organization_money(ctx, organization_id, new_money):
    server_id = ctx.guild.id  
    cursor.execute('UPDATE organizations SET cofre = ? WHERE id = ? AND server_id = ?', (new_money, organization_id, server_id))
    connection.commit()

def get_cost(current_level, improvement_type):
    correct_code = f"{improvement_type} {current_level + 1}"
    
    cursor.execute("SELECT cost FROM store WHERE code = ?", (correct_code,))
    result = cursor.fetchone()
    
    if result is not None:
        cost = result[0]
        return cost
    else:
        return None 

def get_max_level(improvement_type):
    # Defina os níveis máximos para cada tipo de aprimoramento
    max_levels = {
        'scout_level': 3,  # Por exemplo, o nível máximo para 'scout' é 3
        'wish_level': 3,   # O nível máximo para 'wish' é 5
        'business_level': 3,  # E assim por diante
        'claim_level': 2,
    }
    # Retorna o nível máximo correspondente ao tipo de aprimoramento
    return max_levels.get(improvement_type, 0)  # Retorna 0 se o tipo não for encontrado

def calcular_valor_venda(ctx, discord_id, player_name):
    server_id = ctx.guild.id  
    player_name = player_name.lower()  # Converter o nome do jogador fornecido pelo usuário para minúsculas
    cursor.execute('SELECT id FROM allplayers WHERE name = ?', (player_name,))
    player_id = cursor.fetchone()

    if player_id is not None:
        player_id = player_id[0]  # Desempacote o valor do resultado da consulta

        cursor.execute('SELECT price FROM allplayers WHERE id = ?', (player_id,))
        player_price = cursor.fetchone()

        cursor.execute('SELECT selling_tax FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
        organization_selling_tax = cursor.fetchone()

        if player_price is not None and organization_selling_tax is not None:
            player_price = player_price[0]
            organization_selling_tax = organization_selling_tax[0]

            valor_venda = player_price * organization_selling_tax
            return valor_venda

    return None

# Função para verificar se um jogador pertence a um usuário
def isOwner(ctx, player_name, discord_id):
    cursor.execute('SELECT id FROM allplayers WHERE name = ?', (player_name,))
    player_id = cursor.fetchone()
    server_id = ctx.guild.id  

    cursor.execute('SELECT org_id FROM organization_players WHERE server_id = ? AND player_id = ?', (server_id, player_id[0]))
    resultado = cursor.fetchone()
    if resultado[0] == discord_id:
        return True
    else:
        return False

async def get_owner(ctx, player_name):
    cursor.execute('SELECT id FROM allplayers WHERE name = ?', (player_name,))
    player_id = cursor.fetchone()
    server_id = ctx.guild.id  

    cursor.execute('SELECT org_id FROM organization_players WHERE server_id = ? AND player_id = ?', (server_id, player_id[0]))
    org_id = cursor.fetchone()

    if org_id:
        user_id = org_id[0]  # Substitua pelo ID do usuário que você deseja obter informações
        user = await bot.fetch_user(user_id)  # Use 'await' para chamar a função assíncrona

        if user:
            return user.name  # Retorna o nome do usuário
        else:
            return "Desconhecido"  # Retorna "Desconhecido" se o usuário não for encontrado
    else:
        return "Disponível"  # Retorna "Disponível" se o jogador não pertencer a nenhuma organização

def get_icon(nome):
    cursor.execute('SELECT icon FROM allplayers WHERE name = ?', (nome,))
    icon = cursor.fetchone()
    if icon[0] is None:
        return " "
    else:
        return icon[0]




#FUNÇÕES HANDLE/COMANDOS

# Função para lidar com o comando !deletar
@bot.command(name='deletar', hidden=True)
async def deletar(ctx, name):
    if ctx.author.guild_permissions.administrator:  # Only allow administrators to use this command
        if remove_player(ctx, name):
            await ctx.send('Jogador deletado com sucesso.')
        else:
            await ctx.send('Jogador não encontrado.')
    else:
        await ctx.send('Você não tem permissão para usar esse comando.')

# Tratamento de erro para o comando !deletar
@deletar.error
async def deletar_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Formato inválido. Use: !deletar nome_do_jogador', )

# Command to handle !roll
@bot.command(name='roll',
    aliases=['r'],
    brief='Realiza uma rolagem para obter um jogador aleatório.',
    help='Esse comando permite que você role um jogador aleatório. Você deve ter uma organização registrada para usar esse comando. Cada organização tem um limite diário de rolagens. Se você já usou todas as suas rolagens, terá que aguardar até o próximo reset.',
    usage='!roll ou !r')
async def roll(ctx):
    discord_id = ctx.author.id
    
    try:
        # Verificar se o usuário possui uma organização
        organization_id = get_organization(ctx, discord_id)
        if organization_id is None:
            await ctx.send("Você não possui uma organização! Por favor, registre-se usando o comando !registrar antes de tentar rolar!", reference=ctx.message)
            return

        # Verificar se o usuário pode fazer um novo roll
        roll_info = get_roll_info(ctx, organization_id)
        if roll_info and roll_info[0] < roll_info[1]:
            remaining_rolls = roll_info[1] - roll_info[0] - 1
            if remaining_rolls > 0:
                await ctx.send(f"Você ainda tem {remaining_rolls} rolls restantes!")
            else:
                await ctx.send(f"Esse foi o último roll! :skull:")
            increment_roll_count(ctx, organization_id)
            player_id = get_random_player(ctx, discord_id)
            await is_player_available(ctx, player_id)

        else:
            roll_info = get_roll_info(ctx, organization_id)
            time_until_roll_reset = calculate_time_until_reset(reset_roll_count_task)
            await ctx.send(f"Você já usou todas as suas rolagens. Aguarde até o próximo reset em {time_until_roll_reset}.", reference=ctx.message)

    except Exception as e:
        print(f"Ocorreu um erro ao executar o comando !roll: {str(e)}")

# Função para lidar com o comando !org
@bot.command(name='org',
    brief='Exibe informações sobre a organização e o elenco de jogadores.',
    help='Esse comando exibe informações sobre a organização e o elenco de jogadores. Você pode usar o comando sem argumentos para visualizar sua própria organização ou mencionar um membro para ver a organização dele. Se a organização tiver jogadores, uma lista ordenada de jogadores será mostrada juntamente com informações sobre a organização, como nome, sigla e contagem de jogadores.',
    usage='!org [membro]')
async def org(ctx):
    user_id = ctx.author.id
    target_user_id = user_id
    target_user = ctx.author

    # Verifique se um membro foi mencionado
    if ctx.message.mentions:
        target_user = ctx.message.mentions[0]
        target_user_id = target_user.id

    org_id = get_organization(ctx, target_user_id)
    if org_id == None:
        await ctx.send(f'O usuário {target_user} não possui uma organização')
        return

    org_name = get_org_name(ctx, target_user_id)
    org_nick = get_org_nick(ctx, target_user_id)
    org_photo_url = get_org_img(ctx, target_user_id)
    player_count = get_player_count(ctx, target_user_id)
    current_org_sort = get_organization_sort(ctx, target_user_id)
    org_money = get_org_money(ctx, target_user_id)

    elenco = get_sorted_organization(ctx, target_user_id, order_by=current_org_sort)
    elenco_data = []
    for player in elenco:
        player_data = {'name': player[0],'overall': player[1],'team': player[3],'position': player[4]}
        elenco_data.append(player_data)

    if elenco:
        org_view = OrgView(elenco_data, org_photo_url, org_name, org_nick, current_org_sort, target_user, player_count, org_money)
        await org_view.start(ctx)
    else:
        await ctx.send(f'Sua organização não tem nenhum jogador no elenco ou você não tem organização!', reference=ctx.message)

# Função para lidar com o comando !nome
@bot.command(name='nome',
    brief='Atualiza o nome da organização.',
    help='Esse comando permite atualizar o nome da organização. Você deve fornecer um novo nome para a organização como argumento. O nome da organização será atualizado e uma confirmação será enviada como resposta.',
    usage='!nome [novo_nome]')
async def set_org_name(ctx, *, new_org_name):
    update_org_name(ctx, ctx.author.id, new_org_name)
    await ctx.send(f'Nome da organização atualizado para: {new_org_name}', reference=ctx.message)

@set_org_name.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Formato inválido. Use: !nome [nome_novo]', reference=ctx.message)

# Função para lidar com o comando !nome_nick
@bot.command(name='sigla',
    brief='Atualiza a sigla da organização.',
    help='Esse comando permite atualizar a sigla da organização. Você deve fornecer a nova sigla como argumento. A sigla deve ter no máximo 3 letras e ser composta apenas por caracteres alfabéticos. A sigla da organização será atualizada e uma confirmação será enviada como resposta.',
    usage='!sigla [nova_sigla]')
async def set_org_nick(ctx, *, new_org_nick):
    if len(new_org_nick) <= 3:
        update_org_nick(ctx, ctx.author.id, new_org_nick)
        await ctx.send(f'Sigla da organização atualizada para: {new_org_nick}', reference=ctx.message)
    else:
        await ctx.send('Sigla da organização inválida. Certifique-se de que seja uma sigla de até 3 letras.', reference=ctx.message)

@set_org_nick.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Formato inválido. Use: !sigla [nova_sigla]', reference=ctx.message)

# Função para lidar com o comando !imagem
@bot.command(name='imagem',
    brief='Atualiza a imagem da organização.',
    help='Esse comando permite atualizar a imagem da organização. Você deve fornecer um novo url para a imagem da organização como argumento. A imagem da organização será atualizada e uma confirmação será enviada como resposta.',
    usage='!imagem [nova_imagem]')
async def set_org_img(ctx, *, new_org_name):
    update_org_img(ctx, ctx.author.id, new_org_name)
    await ctx.send(f'Imagem da organização atualizada.', reference=ctx.message)

@set_org_img.error
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Formato inválido. Use: !imagem [url_da_imagem]', reference=ctx.message)

# Função para lidar com o comando !busca
@bot.command(name='busca',
    aliases=['pesquisa', 'b', 'p', 's', 'search'],
    brief='Busca, pesquisa e exibe informações sobre jogadores.',
    help='Esse comando permite pesquisar jogadores com base em um ou mais pares de parâmetros e valores especificados. '
         'O parâmetro deve ser um dos atributos dos jogadores, como "nationality", "team", '
         '"position", "league". O valor é o termo de pesquisa que você deseja usar. Se um jogador for '
         'encontrado, suas informações serão exibidas em um embed. Se múltiplos jogadores forem encontrados, '
         'será exibida uma lista paginada com os resultados.\n\n'
         'Pseudônimos dos parâmetros:\n'
         'nationality: country, c, nacionalidade, na, pais, país\n'
         'team: time, t\n'
         'position: posição, posicao, p, r, role\n'
         'league: liga, l, region\n\n',
    usage='!pesquisa [parâmetro1] [valor1] [parâmetro2] [valor2] ... , !b [parâmetro1] [valor1] [parâmetro2] [valor2] ... , '
          '!p [parâmetro1] [valor1] [parâmetro2] [valor2] ... ou !search [parâmetro1] [valor1] [parâmetro2] [valor2] ...')
async def player_pesquisa(ctx, *args):
    if len(args) % 2 != 0:
        embed = discord.Embed(title='Erro de Comando', description='Você deve fornecer pares de parâmetros e valores para a pesquisa.', color=discord.Color.red())
        await ctx.send(embed=embed, reference=ctx.message)
        return

    search_params = {}
    for i in range(0, len(args), 2):
        param, value = args[i], args[i + 1]
        search_params[param] = value

    players = search_players(search_params)

    if players:
        if len(players) == 1:
            player_name = players[0]
            player_details = get_player_details(player_name)
            if player_details:
                name, nationality, team, position, league, photo_url, icon, price = player_details
                dono = await get_owner(ctx, name)
                name = name.upper()
                nationality = nationality.upper()
                team = team.upper()
                position = position.upper()
                league = league.upper()

                embed = discord.Embed(title=f'Jogador: {name}', color=discord.Color.from_rgb(38, 249,255))
                embed.add_field(name='Nacionalidade', value=nationality, inline=False)
                embed.add_field(name='Liga', value=league, inline=False)
                embed.add_field(name='Time', value=team, inline=False)
                embed.add_field(name='Posição', value=position, inline=False)
                embed.add_field(name='Preço', value=price, inline=False)
                embed.add_field(name='Dono', value=dono, inline=False)
                embed.set_image(url=photo_url)
                await ctx.send(embed=embed, reference=ctx.message)
        else:
            search_results_view = SearchResultsView(players, search_params)
            await search_results_view.start(ctx)
    else:
        embed = discord.Embed(title='Nenhum Jogador Encontrado', description=f'Nenhum jogador encontrado com os parâmetros e valores fornecidos.', color=discord.Color.red())
        await ctx.send(embed=embed, reference=ctx.message)

@player_pesquisa.error
async def pesquisa_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title='Erro', description='Formato inválido. Use: !pesquisa parâmetro valor', color=discord.Color.red())
        await ctx.send(embed=embed, reference=ctx.message)
    elif isinstance(error, PlayerNotFoundError):
        embed = discord.Embed(title='Nenhum Jogador Encontrado', description=f'Nenhum jogador encontrado com {error.parameter} igual a "{error.value}".', color=discord.Color.red())
        await ctx.send(embed=embed, reference=ctx.message)

@bot.command(name='vender',
            aliases=['sell'],
            brief='Vende um jogador do seu elenco.',
            help='Esse comando permite vender um jogador do seu elenco. O jogador a ser vendido é especificado pelo nome. Se o jogador for encontrado no seu elenco, uma mensagem de confirmação será enviada para confirmar a venda.',
            usage='!vender [nome_do_jogador]')
async def sell_player(ctx, *, player_name):
    discord_id = ctx.author.id

    # Obtenha o valor da venda do jogador
    valor_recebido = calcular_valor_venda(ctx, discord_id, player_name)

    if valor_recebido:
        # Use a função get_owner para verificar se o jogador pertence ao usuário
        player_name = player_name.lower()
        player_details = get_player_details(player_name)
        _, _, _, _, _, photo_url, _, _ = player_details
        owner_name = await get_owner(ctx, player_name)

        if owner_name is None or owner_name != ctx.author.name:
            embed = discord.Embed(title='Erro', description=f'O jogador {player_name} não pertence a você', color=discord.Color.red())
            await ctx.send(embed=embed, reference=ctx.message)
            return
        
        # Envie um embed com a mensagem de confirmação
        embed = discord.Embed(
            title='Confirmar Venda',
            description=f'Você está prestes a vender o jogador {player_name} por {valor_recebido} moedas.\n\nReaja com <:confirmar:1155491221863665666> para confirmar a venda ou <:recusar:1155491252763107368> para cancelar.',
            color=discord.Color.from_rgb(192, 192,192)
        )
        embed.set_image(url=photo_url)  
        message = await ctx.send(embed=embed)

        # Adicione as reações à mensagem
        await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação
        await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

        try:
            reaction, _ = await bot.wait_for('reaction_add', timeout=30.0, check=check)

            if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
                if venderFunc(ctx, discord_id, player_name, valor_recebido):
                    # Confirmação bem-sucedida
                    embed = discord.Embed(title='Jogador Vendido', description=f'Jogador {player_name} vendido por {valor_recebido} moedas.', color=discord.Color.green())
                else:
                    # O jogador não foi encontrado
                    embed = discord.Embed(title='Erro', description=f'Jogador {player_name} não encontrado no seu elenco.', color=discord.Color.red())
            else:
                # Venda cancelada pelo usuário
                embed = discord.Embed(title='Venda Cancelada', description=f'A venda do jogador {player_name} foi cancelada.', color=discord.Color.from_rgb(192, 192, 192))

            # Atualize a mensagem com a resposta
            await message.edit(embed=embed)
        except asyncio.TimeoutError:
            pass
    else:
        # O jogador não foi encontrado
        embed = discord.Embed(title='Erro', description=f'Jogador {player_name} não encontrado no seu elenco.', color=discord.Color.red())
        await ctx.send(embed=embed, reference=ctx.message)

@sell_player.error
async def sell_player_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title='Erro', description='Formato inválido. Use: !vender [nome_do_jogador]', color=discord.Color.red())
        await ctx.send(embed=embed, reference=ctx.message)

# Função SortByName
@bot.command(name='ordenar_nome',
    aliases=['sort_by_name', 'sn', 'on'],
    brief='Ordena os jogadores do seu elenco pelo nome.',
    help='Esse comando permite ordenar os jogadores do seu elenco em ordem alfabética pelo nome. A lista ordenada será exibida em páginas, permitindo uma visualização mais organizada. Se você não tiver jogadores na sua organização, ou se os detalhes dos jogadores estiverem faltando, uma mensagem adequada será exibida.',
    usage='!ordenar_nome , !sort_by_name , !sn ou !on')
async def sort_by_name(ctx):
    user_id = ctx.author.id
    org_players = get_organization_players(ctx, user_id)

    if not org_players:
        await ctx.send(f'Você não tem uma organização ou sua organização está vazia.', reference=ctx.message)
        return

    org_players = list(filter(None, org_players))
    player_details_list = [get_player_details_by_id(player_id) for player_id in org_players]

    # Remove None values from player_details_list
    player_details_list = [player_details for player_details in player_details_list if player_details]

    sorted_player_details = sorted(player_details_list, key=lambda details: details[0].lower())  # Ordenar os detalhes pelo nome

    message = ''
    for player_details in sorted_player_details:
        player_name, _, _, _, _, _, _, _ = player_details
        message += f'{player_name}\n'

    embed, paginated_view = get_sorted_paginated_view(message.split('\n'), sort_parameter='Nome')
    update_organization_sort(ctx, user_id, 'name')
    await ctx.send(embed=embed, view=paginated_view, reference=ctx.message)

# Função SortByCountry
@bot.command(name='ordenar_país',
    aliases=['sort_by_country', 'sc', 'op'],
    brief='Ordena os jogadores do seu elenco por nacionalidade.',
    help='Esse comando permite ordenar os jogadores do seu elenco por nacionalidade. Os jogadores serão agrupados por país e listados em páginas separadas. Se você não tiver jogadores na sua organização ou se os detalhes dos jogadores estiverem faltando, uma mensagem adequada será exibida.',
    usage='!ordenar_país , !sort_by_country , !sc ou !op')
async def sort_by_country(ctx):
    user_id = ctx.author.id
    org_players = get_organization_players(ctx, user_id)

    if not org_players:
        await ctx.send(f'Você não tem uma organização ou sua organização está vazia.', reference=ctx.message)
        return

    players_by_country = {}  # Criação de um dicionário para agrupar jogadores por nacionalidade

    for player_name in org_players:
        player_details = get_player_details_by_id(player_name)
        if player_details:
            _, nationality, _, _, _, _, _, _ = player_details
            if nationality not in players_by_country:
                players_by_country[nationality] = []
            players_by_country[nationality].append(player_name)
    
    sorted_countries = sorted(players_by_country.keys())

    message = ''
    for country in sorted_countries:
        player_ids = players_by_country[country]
        
        players_list = ""
        for player_id in player_ids:
            player_details = get_player_details_by_id(player_id)
            if player_details:
                player_name, _, _, _, _, _, _, _ = player_details
                players_list += f"{player_name}\n"
        
        message += f'**{country}**:\n{players_list}\n\n'
        message += '\n'

    embed, paginated_view = get_sorted_paginated_view(message.split('\n\n'), sort_parameter='Nacionalidade')
    update_organization_sort(ctx, user_id, 'nationality')  

    await ctx.send(embed=embed, view=paginated_view, reference=ctx.message)

# Função SortByTeam
@bot.command(name='ordenar_time',
    aliases=['sort_by_team', 'st', 'ot'],
    brief='Ordena os jogadores do seu elenco por time.',
    help='Esse comando permite ordenar os jogadores do seu elenco por time. Os jogadores serão agrupados por time e listados em páginas separadas. Se você não tiver jogadores na sua organização ou se os detalhes dos jogadores estiverem faltando, uma mensagem adequada será exibida.',
    usage='!ordenar_time , !sort_by_team , !st ou !ot')
async def sort_by_team(ctx):
    user_id = ctx.author.id
    org_players = get_organization_players(ctx, user_id)

    if not org_players:
        await ctx.send(f'Você não tem uma organização ou sua organização está vazia.', reference=ctx.message)
        return

    players_by_team = {}  # Criação de um dicionário para agrupar jogadores por time

    for player_name in org_players:
        player_details = get_player_details_by_id(player_name)
        if player_details:
            _, _, team, _, _, _, _, _ = player_details
            if team not in players_by_team:
                players_by_team[team] = []
            players_by_team[team].append(player_name)
    
    sorted_teams = sorted(players_by_team.keys())

    message = ''
    for team in sorted_teams:
        player_ids = players_by_team[team]
        
        players_list = ""
        for player_id in player_ids:
            player_details = get_player_details_by_id(player_id)
            if player_details:
                player_name, _, _, _, _, _, _, _ = player_details
                players_list += f"{player_name}\n"
        
        message += f'**{team}**:\n{players_list}\n\n'
        message += '\n'

    embed, paginated_view = get_sorted_paginated_view(message.split('\n\n'), sort_parameter='Time')
    update_organization_sort(ctx, user_id, 'team')  
    await ctx.send(embed=embed, view=paginated_view, reference=ctx.message)

# Função SortByRole
@bot.command(name='ordenar_role',
    aliases=['sort_by_role', 'sr', 'or'],
    brief='Ordena os jogadores do seu elenco por posição (role).',
    help='Esse comando permite ordenar os jogadores do seu elenco por posição (role). Os jogadores serão agrupados por posição (top, jungle, mid, adc, sup) e listados em páginas separadas. Se você não tiver jogadores na sua organização ou se os detalhes dos jogadores estiverem faltando, uma mensagem adequada será exibida.',
    usage = '!ordenar_role , !sort_by_role , !sr , !or')
async def sort_by_role(ctx):
    user_id = ctx.author.id
    org_players = get_organization_players(ctx, user_id)

    if not org_players:
        await ctx.send(f'Você não tem uma organização ou sua organização está vazia.', reference=ctx.message)
        return

    players_by_position = {}  # Criação de um dicionário para agrupar jogadores por posição

    for player_name in org_players:
        player_details = get_player_details_by_id(player_name)
        if player_details:
            _, _, _, position, _, _, _, _ = player_details
            if position not in players_by_position:
                players_by_position[position] = []
            players_by_position[position].append(player_name)

    # Define a ordem das posições
    position_order = ['Top', 'Jungle', 'Mid', 'Adc', 'Sup']

    message = ''
    for position in position_order:
        if position in players_by_position:
            player_ids = players_by_position[position]

            players_list = ""
            for player_id in player_ids:
                player_details = get_player_details_by_id(player_id)
                if player_details:
                    player_name, _, _, _, _, _, _, _ = player_details
                    players_list += f"{player_name}\n"

            message += f'**{position}**:\n{players_list}\n\n'

    embed, paginated_view = get_sorted_paginated_view(message.split('\n\n'), sort_parameter='Role')
    update_organization_sort(ctx, user_id, 'position')
    await ctx.send(embed=embed, view=paginated_view, reference=ctx.message)

# Função SortByOverall
@bot.command(name='ordenar_overall',
    aliases=['sort_by_overall', 'so', 'oo'],
    brief='Ordena os jogadores do seu elenco por classificação geral (overall).',
    help='Esse comando permite ordenar os jogadores do seu elenco por classificação geral (overall). Os jogadores serão listados em ordem decrescente de overall. Se você não tiver jogadores na sua organização ou se os detalhes dos jogadores estiverem faltando, uma mensagem adequada será exibida.',
    usage='!ordenar_overall , !sort_by_overall , !so ou !oo')
async def sort_by_overall(ctx):
    user_id = ctx.author.id
    org_players = get_organization_players(ctx, user_id)

    if not org_players:
        await ctx.send(f'Você não tem uma organização ou sua organização está vazia.', reference=ctx.message)
        return

    sorted_players = sorted(org_players, key=get_player_overall, reverse=True)

    message = ''
    for player_id in sorted_players:
        player_details = get_player_details_by_id(player_id)
        if player_details:
            player_name, _, _, _, _, _ ,_, _ = player_details
            player_overall = get_player_overall(player_id)
            message += f'{player_overall} | {player_name}\n'
    
    embed, paginated_view = get_sorted_paginated_view(message.split('\n'), sort_parameter='Overall')
    update_organization_sort(ctx, user_id, 'overall')  
    await ctx.send(embed=embed, view=paginated_view, reference=ctx.message)

# Função SortByLeague
@bot.command(name='ordenar_liga',
    aliases=['sort_by_league', 'sl', 'ol'],
    brief='Ordena os jogadores do seu elenco por liga.',
    help='Esse comando permite ordenar os jogadores do seu elenco por liga. Os jogadores serão agrupados e listados por liga em ordem alfabética. Se você não tiver jogadores na sua organização ou se os detalhes dos jogadores estiverem faltando, uma mensagem adequada será exibida.',
    usage='!ordenar_liga , !sort_by_league , !sl ou !ol')
async def sort_by_league(ctx):
    user_id = ctx.author.id
    org_players = get_organization_players(ctx, user_id)

    if not org_players:
        await ctx.send(f'Você não tem uma organização ou sua organização está vazia.', reference=ctx.message)
        return

    players_by_league = {}  # Dicionário para agrupar jogadores por liga

    for player_name in org_players:
        player_details = get_player_details_by_id(player_name)
        if player_details:
            _, _, _, _, league, _, _, _ = player_details
            if league not in players_by_league:
                players_by_league[league] = []
            players_by_league[league].append(player_name)

    sorted_leagues = sorted(players_by_league.keys())  # Ordena as ligas em ordem alfabética

    message = ''
    for league in sorted_leagues:
        player_ids = players_by_league[league]

        players_list = ""
        for player_id in player_ids:
            player_details = get_player_details_by_id(player_id)
            if player_details:
                player_name, _, _, _, _, _, _, _ = player_details
                players_list += f"{player_name}\n"

        message += f'**{league}**:\n{players_list}\n\n'

    embed, paginated_view = get_sorted_paginated_view(message.split('\n\n'), sort_parameter='Liga')
    update_organization_sort(ctx, user_id, 'league')
    await ctx.send(embed=embed, view=paginated_view, reference=ctx.message)

@bot.command(name='registrar',
    brief='Registra um usuário e sua organização.',
    help='Esse comando permite registrar um usuário e sua organização no sistema. Se o usuário já estiver registrado, será exibida uma mensagem informando que o registro já foi realizado. Caso contrário, o usuário será adicionado ao banco de dados com as informações iniciais da organização.',
    usage='!registrar')
async def registrar(ctx):
    try:
        discord_id = ctx.author.id
        server_id = ctx.guild.id
        org_img_url = ctx.author.avatar.url  # Obtenha a URL do avatar do usuário

        # Verificar se o usuário já está registrado no banco de dados
        cursor.execute('SELECT id FROM organizations WHERE id = ? AND server_id = ?', (discord_id, server_id))
        existing_user = cursor.fetchone()

        if existing_user:
            await ctx.send('Você já está registrado.', reference=ctx.message)
        else:
            # Adicionar o novo usuário ao banco de dados com player_count inicial como 0 e reset_time definido
            cursor.execute('INSERT INTO organizations (id, server_id, org_name, org_nick, player_count, org_img) VALUES (?, ?, ?, ?, ?, ?)', (discord_id, server_id , 'Nome da Org', 'AAA', 0, org_img_url))
            connection.commit()

            # Inserir uma entrada correspondente na tabela improvements
            cursor.execute('INSERT INTO improvements (org_id, server_id) VALUES (?, ?)', (discord_id, server_id))
            connection.commit()

            await ctx.send('Registro bem-sucedido. Seja bem-vindo invocador!', reference=ctx.message)

    except Exception as e:
        print(f"Ocorreu um erro ao registrar o usuário: {e}")
        await ctx.send('Desculpe, ocorreu um erro ao registrar o usuário.', reference=ctx.message)

# Função para ver as informações de um jogador.
@bot.command(name='info', brief='Exibe informações detalhadas sobre um jogador.')
async def player_info(ctx, *, player_name):
    player_name = player_name.lower()
    
    try:
        cursor.execute('SELECT name FROM allplayers WHERE name LIKE ?', (f'%{player_name}%',))
        player_info_data = [row[0] for row in cursor.fetchall()]

        if not player_info_data:
            embed = discord.Embed(title='Nenhum Jogador Encontrado', description=f'Nenhum jogador encontrado com nome similar a "{player_name}".', color=discord.Color.red())
            await ctx.send(embed=embed, reference=ctx.message)
            return

        player_info_view = PlayerInfoView(ctx, player_info_data)
        await player_info_view.show()
    except Exception as e:
        await ctx.send(f"Ocorreu um erro ao buscar informações do jogador: {str(e)}")

@player_info.error
async def player_info_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title='Erro', description='Formato inválido. Use: !info nome_do_jogador', color=discord.Color.red())
        await ctx.send(embed=embed, reference = ctx.message)
    elif isinstance(error, PlayerNotFoundError):
        embed = discord.Embed(title='Nenhum Jogador Encontrado', description=f'Nenhum jogador encontrado com nome igual a "{error.value}".', color=discord.Color.red())
        await ctx.send(embed=embed, reference = ctx.message)


# Comando para exibir detalhes do usuário
@bot.command(name='detalhes',
    aliases=['d'],
    brief='Exibe detalhes sobre a quantidade de claims e rolls disponíveis, além do tempo até o próximo reset.',
    help='Esse comando permite visualizar detalhes sobre a quantidade de claims e rolls disponíveis para o usuário. Também mostra o tempo restante até o próximo reset de claims e rolls.',
    usage='!detalhes ou !d')
async def detalhes(ctx):
    discord_id = ctx.author.id
    organization_id = get_organization(ctx, discord_id)
        
    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return
        
    claim_info = get_claim_info(ctx, organization_id)
    roll_info = get_roll_info(ctx, organization_id)
    time_until_claim_reset = calculate_time_until_reset(reset_claim_count_task)
    time_until_roll_reset = calculate_time_until_reset(reset_roll_count_task)
    
    claims_available = claim_info[1] - claim_info[0]
    rolls_available = roll_info[1] - roll_info[0]
    
    # Obtenha o dinheiro da organização
    organization_money = get_org_money(ctx, organization_id)

    embed = discord.Embed(title="Detalhes do Usuário", color=discord.Color.from_rgb(38, 249,255))
    embed.set_author(name=bot_name, icon_url=bot_photo_url)
    embed.add_field(name="**Claims**", value=f"{claims_available} de {claim_info[1]}", inline=True)
    embed.add_field(name="**Rolls**", value=f"{rolls_available} de {roll_info[1]}", inline=True)
    embed.add_field(name="**Dinheiro**", value=organization_money, inline=False)
    embed.add_field(name="Reset de Claims: ", value=time_until_claim_reset, inline=False)
    embed.add_field(name="Reset de Rolls: ", value=time_until_roll_reset, inline=False)
        
    await ctx.send(embed=embed, reference=ctx.message)

@bot.command(name='loja',
             brief='Exibe a lista de aprimoramentos disponíveis para compra na loja.',
             help='Esse comando exibe a lista de aprimoramentos disponíveis na loja que podem ser comprados. Mostra o nome, descrição e custo de cada aprimoramento.',
             usage='!loja')
async def loja(ctx):
    user_id = ctx.author.id

    # Busca informações da organização do usuário
    organization_id = get_organization(ctx, user_id)
    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return

    user_improvements = get_improvements_info(ctx, ctx.author.id)

    if user_improvements is None:
        await ctx.send("Não foi possível obter informações sobre os aprimoramentos da sua organização.")
        return

    # Busca a lista de aprimoramentos da loja
    available_improvements = []
    max_level_improvements = []  # Lista para aprimoramentos no nível máximo
    store = get_improvements_from_database()
    column_names = {0: 'scout_level', 1: 'wish_level', 2: 'business_level', 3: 'claim_level'}

    for idx, improvement_code in enumerate(user_improvements):
        for improvement in store:
            _, _, _, _, _, code = improvement
            level = user_improvements[idx]

            next_level = str(level + 1)
            max_level = get_max_level(column_names.get(idx))

            if f"{column_names.get(idx)} {next_level}" == code:
                if level < max_level:
                    available_improvements.append(improvement)
            elif f"{column_names.get(idx)} {level}" == code:
                if level == max_level:
                    max_level_improvements.append(improvement)

    if available_improvements or max_level_improvements:
        organization_name = get_org_name(ctx, organization_id)
        organization_money = get_org_money(ctx, organization_id)
        embed = create_store_embed(organization_name, organization_money, available_improvements, max_level_improvements)
        await ctx.send(embed=embed, reference=ctx.message)

@bot.command(name='epico',
             aliases=['Equipe de Scout', 'Equipe'],
             brief='Compra um nível do aprimoramento "Equipe de Scout".',
             help='Este comando permite que você compre um nível adicional do benefício "Equipe de Scout" para aprimorar a habilidade de encontrar jogadores raros. '
                  'Cada nível melhora suas chances de encontrar jogadores de maior raridade nas rolagens.',
             usage='!epico')
async def comprar_scout(ctx):
    server_id = ctx.guild.id  
    user_id = ctx.author.id
    organization_id = get_organization(ctx, user_id)

    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return

    user_improvements = get_improvements_info(ctx, organization_id)
    if user_improvements is None:
        await ctx.send("Não foi possível obter informações sobre os aprimoramentos da sua organização.")
        return

    scout_level = user_improvements[0]  # Índice correto para 'scout_level'
    
    # Verificar se o nível do Scout já está no máximo
    if scout_level >= 3:  # Substitua MAX_SCOUT_LEVEL pelo valor máximo permitido
        await ctx.send("O benefício 'Épico' já está no nível máximo.")
        return

    scout_cost = get_cost(scout_level, "scout_level")  # Função que retorna o custo do próximo nível de "scout"

    embed = discord.Embed(title="Compra de Benefício: Equipe de Scout",
                          description=f"Você está prestes a comprar o próximo nível do benefício 'Épico'.\n\n**Nível Atual:** {scout_level}\n**Custo:** {scout_cost} moedas",
                          color=discord.Color.from_rgb(255, 0, 255))
    embed.set_author(name=bot_name, icon_url=bot_photo_url)
    embed.add_field(name="", value = "Reaja com <:confirmar:1155491221863665666> para confirmar a compra ou <:recusar:1155491252763107368> para cancelar.")
    message = await ctx.send(embed=embed, reference=ctx.message)

    # Adicionar reações à mensagem para permitir que o usuário confirme ou cancele
    await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
    await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)

        if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
            organization_money = get_org_money(ctx, organization_id)

            if organization_money >= scout_cost:
                # Efetuar a compra e atualizar o nível do benefício "scout"
                new_scout_level = scout_level + 1
                update_level(ctx, organization_id, 'scout_level', new_scout_level)  # Atualizar o nível no banco de dados
                update_organization_money(ctx, organization_id, organization_money - scout_cost)
                
                # Atualizar também roll_max
                cursor.execute("UPDATE organizations SET roll_max = roll_max + ? WHERE id = ? AND server_id = ?", (new_scout_level, organization_id, server_id))
                connection.commit()
                
                await ctx.send(f"Compra do benefício 'Épico' realizada com sucesso! O nível de 'Equipe de Scout' foi atualizado para {new_scout_level}.", reference = ctx.message)
            else:
                await ctx.send("Dinheiro insuficiente para comprar este benefício.", reference = ctx.message)
        else:
            pass
    except asyncio.TimeoutError:
        pass

@bot.command(name='lendario',
             aliases=['Na Mira', 'Mira'],
             brief='Compra um nível do aprimoramento "Na Mira" para melhorar as chances de obter jogadores desejados.',
             help='Este comando permite que você compre um nível do aprimoramento "Na Mira" para melhorar suas chances de obter jogadores raros na sua organização. Cada nível do "Na Mira" aumenta sua taxa de sucesso ao buscar jogadores raros e o número máximo de jogadores que você pode adicionar à sua lista de Interesses',
             usage='!lendario')
async def comprar_wish(ctx):
    server_id = ctx.guild.id  
    user_id = ctx.author.id
    organization_id = get_organization(ctx, user_id)
    
    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return

    user_improvements = get_improvements_info(ctx, organization_id)
    if user_improvements is None:
        await ctx.send("Não foi possível obter informações sobre os aprimoramentos da sua organização.")
        return

    wish_level = user_improvements[1]  # Índice correto para 'wish_level'
    
    # Verificar se o nível do Wish já está no máximo
    if wish_level >= 3:  # Substitua MAX_WISH_LEVEL pelo valor máximo permitido
        await ctx.send("O benefício 'Lendário' já está no nível máximo.")
        return
    
    wish_cost = get_cost(wish_level, "wish_level")  # Função que retorna o custo do próximo nível de "wish"

    embed = discord.Embed(title="Compra de Benefício: Na Mira",
                          description=f"Você está prestes a comprar o próximo nível do benefício 'Lendário'.\n\n**Nível Atual:** {wish_level}\n**Custo:** {wish_cost} moedas",
                          color=discord.Color.from_rgb(255, 0, 255))
    embed.set_author(name=bot_name, icon_url=bot_photo_url)
    embed.add_field(name="", value = "Reaja com <:confirmar:1155491221863665666> para confirmar a compra ou <:recusar:1155491252763107368> para cancelar.")
    message = await ctx.send(embed=embed, reference=ctx.message)

    # Adicionar reações à mensagem para permitir que o usuário confirme ou cancele
    await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
    await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)

        if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
            organization_money = get_org_money(ctx, organization_id)
            
            if organization_money >= wish_cost:
                # Efetuar a compra e atualizar o nível do benefício "wish"
                new_wish_level = wish_level + 1
                update_level(ctx, organization_id, 'wish_level', new_wish_level)
                update_organization_money(ctx, organization_id, organization_money - wish_cost)
                
                # Atualizar também as colunas wish_rate e wish_max
                cursor.execute("UPDATE organizations SET wish_rate = wish_rate + ?, wish_max = wish_max + ? WHERE id = ? AND server_id = ?", (new_wish_level * 0.25, new_wish_level, organization_id, server_id))
                connection.commit()
                
                await ctx.send(f"Compra do benefício 'Épico' realizada com sucesso! O nível de 'Na Mira' foi atualizado para {new_wish_level}.", reference = ctx.message)
            else:
                await ctx.send("Dinheiro insuficiente para comprar este benefício.", reference = ctx.message)
        else:
            pass
    except asyncio.TimeoutError:
        pass

@bot.command(name='mitico',
             aliases=['Grandes Negócios', 'Grandes', 'Negócios', 'Negocios'],
             brief='Compra um nível do aprimoramento "Grandes Negócios" para melhorar as operações comerciais.',
             help='Este comando permite que você compre um nível do aprimoramento "Grandes Negócios" para melhorar suas operações comerciais na sua organização. Cada nível de "Grandes Negócios" aumenta seus lucros ao vender jogadores.',
             usage='!mitico')
async def comprar_business(ctx):
    server_id = ctx.guild.id  
    user_id = ctx.author.id
    organization_id = get_organization(ctx, user_id)

    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return

    user_improvements = get_improvements_info(ctx, organization_id)
    if user_improvements is None:
        await ctx.send("Não foi possível obter informações sobre os aprimoramentos da sua organização.")
        return

    business_level = user_improvements[2]  # Índice correto para 'business_level'

    # Verificar se o nível do Business já está no máximo
    if business_level >= 3:  # Substitua 3 pelo valor máximo permitido
        await ctx.send("O benefício 'Mítico' já está no nível máximo.")
        return

    business_cost = get_cost(business_level, "business_level")  # Função que retorna o custo do próximo nível de "business"

    embed = discord.Embed(title="Compra de Benefício: Grandes Negócios",
                          description=f"Você está prestes a comprar o próximo nível do benefício 'Mítico'.\n\n**Nível Atual:** {business_level}\n**Custo:** {business_cost} moedas",
                          color=discord.Color.from_rgb(255, 0, 255))
    embed.set_author(name=bot_name, icon_url=bot_photo_url)
    embed.add_field(name="", value = "Reaja com <:confirmar:1155491221863665666> para confirmar a compra ou <:recusar:1155491252763107368> para cancelar.")
    message = await ctx.send(embed=embed, reference=ctx.message)

    # Adicionar reações à mensagem para permitir que o usuário confirme ou cancele
    await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
    await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)

        if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
            organization_money = get_org_money(ctx, organization_id)

            if organization_money >= business_cost:
                # Efetuar a compra e atualizar o nível do benefício "business"
                new_business_level = business_level + 1
                update_level(ctx, organization_id, 'business_level', new_business_level)  # Atualizar o nível no banco de dados
                update_organization_money(ctx, organization_id, organization_money - business_cost)

                # Atualizar também as colunas selling_tax e selling_max
                cursor.execute("UPDATE organizations SET selling_tax = selling_tax + ?, selling_max = selling_max + ? WHERE id = ? AND server_id = ?", (0.1, 0.5, organization_id, server_id))
                connection.commit()

                await ctx.send(f"Compra do benefício 'Épico' realizada com sucesso! O nível de 'Grandes Negócios' foi atualizado para {new_business_level}.", reference = ctx.message)
            else:
                await ctx.send("Dinheiro insuficiente para comprar este benefício.", reference = ctx.message)
        else:
            pass
    except asyncio.TimeoutError:
        pass

@bot.command(name='ultimate',
             aliases=['Novos Investimentos', 'Novos', 'Investimentos'],
             brief='Compra um nível do aprimoramento "Novos Investimentos."',
             help='Este comando permite que você compre um nível do aprimoramento "Novos Investimentos" para sua organização. Isso permite que você reivindique mais jogadores',
             usage='!ultimate')
async def comprar_claim(ctx):
    server_id = ctx.guild.id  
    user_id = ctx.author.id
    organization_id = get_organization(ctx, user_id)

    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return

    user_improvements = get_improvements_info(ctx, organization_id)
    if user_improvements is None:
        await ctx.send("Não foi possível obter informações sobre os aprimoramentos da sua organização.")
        return

    claim_level = user_improvements[3]  # Índice correto para 'claim_level'

    # Verificar se o nível do Claim já está no máximo
    if claim_level >= 2:  # Substitua MAX_CLAIM_LEVEL pelo valor máximo permitido
        await ctx.send("O benefício 'Ultimate' já está no nível máximo.")
        return

    claim_cost = get_cost(claim_level, "claim_level")  # Função que retorna o custo do próximo nível de "claim"

    embed = discord.Embed(title="Compra de Benefício: Novos Investimentos",
                          description=f"Você está prestes a comprar o próximo nível do benefício 'Ultimate'.\n\n**Nível Atual:** {claim_level}\n**Custo:** {claim_cost} moedas",
                          color=discord.Color.from_rgb(255, 0, 255))
    embed.set_author(name=bot_name, icon_url=bot_photo_url)
    embed.add_field(name="", value = "Reaja com <:confirmar:1155491221863665666> para confirmar a compra ou <:recusar:1155491252763107368> para cancelar.")
    message = await ctx.send(embed=embed, reference=ctx.message)
    
    # Adicionar reações à mensagem para permitir que o usuário confirme ou cancele
    await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
    await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)

        if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
            organization_money = get_org_money(ctx, organization_id)

            if organization_money >= claim_cost:
                # Efetuar a compra e atualizar o nível do benefício "claim"
                new_claim_level = claim_level + 1
                update_level(ctx, organization_id, 'claim_level', new_claim_level)
                update_organization_money(ctx, organization_id, organization_money - claim_cost)

                # Atualizar também claim_max
                cursor.execute("UPDATE organizations SET claim_max = claim_max + ? WHERE id = ? AND server_id = ?", (1, organization_id, server_id))
                connection.commit()

                await ctx.send(f"Compra do benefício 'Épico' realizada com sucesso! O nível de 'Novos Investimentos' foi atualizado para {new_claim_level}.", reference = ctx.message)
            else:
                await ctx.send("Dinheiro insuficiente para comprar este benefício.", reference = ctx.message)

        else:
            pass

    except asyncio.TimeoutError:
        pass

@bot.command(name='dinheiro', hidden = True)
async def definir_dinheiro(ctx):
    user_id = ctx.author.id
    organization_id = get_organization(ctx, user_id)
    
    if organization_id is None:
        await ctx.send("Você não possui uma organização! Use o comando !registrar para se registrar.")
        return

    # Define o valor do dinheiro da organização como 10,000,000 moedas
    org_money = get_org_money(ctx, ctx.author.id)
    update_organization_money(ctx, ctx.author.id, org_money + 1000000)
    await ctx.send("O valor do dinheiro da organização foi definido para 10,000,000 moedas.")

@bot.command(name='scout',
             brief='Adiciona um jogador aos seus Interesses.',
             usage='!scout [nome do jogador]',
             help= 'Este comando permite que você adicione um jogador aos seus Interesses. Você precisa fornecer o nome do jogador como argumento. Sua lista de Interesses tem um limite, portanto, verifique se você não atingiu o limite antes de adicionar um novo jogador.')
async def add_to_wishlist(ctx, player_name: str):
    server_id = ctx.guild.id  
    player_name = player_name.lower()
    # Verifique se o jogador está na lista all_players
    cursor.execute('SELECT id, photo_url FROM allplayers WHERE name = ?', (player_name,))
    result = cursor.fetchone()

    if result:
        # Obtenha o ID e a photo_url do jogador da lista all_players
        player_id, photo_url = result[0], result[1]

        # Verifique se o usuário já está registrado
        cursor.execute('SELECT id FROM organizations WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
        result = cursor.fetchone()

        if result:
            # O usuário está registrado, então obtenha sua wish_list atual e wish_max
            cursor.execute('SELECT wish_list, wish_max FROM organizations WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
            result = cursor.fetchone()
            current_wishlist = result[0]
            wish_max = result[1]

            # Converta a wish_list atual em uma lista de IDs
            wish_list_ids = [int(id_str) for id_str in current_wishlist.split(',')] if current_wishlist else []

            # Verifique se a wish_list já está cheia
            if len(wish_list_ids) >= wish_max:
                await ctx.send("Sua lista está cheia. Remova um jogador antes de adicionar mais.",reference = ctx.message)
            else:
                # Verifique se o jogador já está na wish_list
                if player_id in wish_list_ids:
                    await ctx.send(f"{player_name} já está em seus Interesses.", reference = ctx.message)
                else:
                    # Criar um embed com a foto do jogador e uma mensagem de confirmação
                    embed = discord.Embed(title=f"Adicionar {player_name} à Interesses?",
                                            description=f"Clique no emoji <:confirmar:1155491221863665666> abaixo para confirmar ou <:recusar:1155491252763107368> para cancelar.",
                                            color=discord.Color.from_rgb(192, 192, 192))
                    embed.set_image(url=photo_url)

                    # Enviar o embed e aguardar a reação do usuário
                    message = await ctx.send(embed=embed)
                    await message.add_reaction('<:confirmar:1155491221863665666>')  # Emoji de confirmação
                    await message.add_reaction('<:recusar:1155491252763107368>')  # Emoji de cancelamento

                    # Função para verificar a reação do usuário
                    def check(reaction, user):
                        return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)

                        if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
                            # Adicionar o jogador à wish_list
                            wish_list_ids.append(player_id)

                            # Atualizar a wish_list no banco de dados
                            cursor.execute('UPDATE organizations SET wish_list = ? WHERE id = ? AND server_id = ?', (','.join(map(str, wish_list_ids)), ctx.author.id, server_id))
                            connection.commit()
                            await ctx.send(f"{player_name} foi adicionado à seus Interesses.", reference = ctx.message)
                        else:
                            pass
                    except asyncio.TimeoutError:
                        pass
        else:
            await ctx.send("Você não está registrado. Use o comando `!registrar` para se registrar e criar uma Lista de Interesses.", reference = ctx.message)
    else:
        await ctx.send(f"{player_name} não foi encontrado na lista de jogadores. Por favor verifique o nome passado!", reference = ctx.message)

@add_to_wishlist.error
async def add_to_wishlist_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title='Erro', description='Formato inválido. Use: !scout [nome do jogador]', color=discord.Color.red())
        await ctx.send(embed=embed, reference = ctx.message)
    elif isinstance(error, Exception):
        await ctx.send(f"Ocorreu um erro ao processar o comando. Detalhes do erro: {str(error)}", reference = ctx.message)

@bot.command(name='remover',
             brief='Remove um jogador dos seus Interesses.',
             usage='!remover [nome do jogador]',
             help='Este comando permite que você remova um jogador de seus Interesses. Você precisa fornecer o nome do jogador como argumento. Se o jogador estiver em seus Interesses, ele será removido. Caso contrário, você receberá uma mensagem informando que o jogador não está na sua lista de Interesses.')
async def remove_from_wishlist(ctx, player_name: str):
    server_id = ctx.guild.id  
    # Verifique se o usuário está registrado
    cursor.execute('SELECT id FROM organizations WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
    result = cursor.fetchone()

    if result:
        # O usuário está registrado, então obtenha sua wish_list atual
        cursor.execute('SELECT wish_list FROM organizations WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
        current_wishlist = cursor.fetchone()[0]

        if current_wishlist:
            # Converta a wish_list atual em uma lista de IDs
            wish_list_ids = [int(id_str) for id_str in current_wishlist.split(',')]

            # Verifique se o jogador está na wish_list
            cursor.execute('SELECT id FROM allplayers WHERE name = ?', (player_name,))
            player_id = cursor.fetchone()

            if player_id:
                # Obtenha o ID do jogador da lista all_players
                player_id = player_id[0]

                if player_id in wish_list_ids:
                    # Remova o jogador da wish_list
                    wish_list_ids.remove(player_id)

                    # Atualize a wish_list no banco de dados
                    cursor.execute('UPDATE organizations SET wish_list = ? WHERE id = ? AND server_id = ?', (','.join(map(str, wish_list_ids)), ctx.author.id, server_id))
                    connection.commit()
                    await ctx.send(f"{player_name} foi removido de seus Interesses.", reference = ctx.message)
                else:
                    await ctx.send(f"{player_name} não está em seus Interesses.", reference = ctx.message)
            else:
                await ctx.send(f"{player_name} não foi encontrado na lista de jogadores. Por favor verifique o nome passado!", reference = ctx.message)
        else:
            await ctx.send("Interesses está vazio.", reference = ctx.message)
    else:
        await ctx.send("Você não está registrado. Use o comando `!registrar` para se registrar e criar uma wish_list.", reference = ctx.message)

@remove_from_wishlist.error
async def remove_from_wishlist_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title='Erro', description='Formato inválido. Use: !remover [nome do jogador]', color=discord.Color.red())
        await ctx.send(embed=embed, reference = ctx.message)
    elif isinstance(error, Exception):
        await ctx.send(f"Ocorreu um erro ao processar o comando. Detalhes do erro: {str(error)}", reference = ctx.message)

@bot.command(name='interesses',
             brief='Exibe a lista de jogadores em seus Interesses ou de outro membro mencionado.',
             usage='!interesses [membro mencionado]',
             help='Este comando permite que você visualize a lista de jogadores em seus Interesses ou os Interesses de outro membro mencionado. Se você ainda não adicionou nenhum jogador aos seus Interesses, a lista estará vazia. Use o comando `!scout` para adicionar jogadores à sua lista de Interesses.')
async def view_wishlist(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    server_id = ctx.guild.id  
    # Verifique se o usuário está registrado
    cursor.execute('SELECT id FROM organizations WHERE id = ? AND server_id = ?', (member.id, server_id))
    result = cursor.fetchone()

    if result:
        # O usuário está registrado, então obtenha sua wish_list atual
        cursor.execute('SELECT wish_list FROM organizations WHERE id = ? AND server_id = ?', (member.id, server_id))
        current_wishlist = cursor.fetchone()[0]

        if current_wishlist:
            # Converta a wish_list atual em uma lista de IDs
            wish_list_ids = [int(id_str) for id_str in current_wishlist.split(',')]

            if wish_list_ids:
                # Consulte o banco de dados para obter os nomes dos jogadores na wish_list
                cursor.execute('SELECT name FROM allplayers WHERE id IN ({})'.format(','.join(map(str, wish_list_ids))))
                wishlist_players = cursor.fetchall()

                # Crie uma mensagem com os nomes dos jogadores na wish_list
                wishlist_message = f'Interesses de {member.display_name}:\n'
                for player in wishlist_players:
                    wishlist_message += f"- {player[0]}\n"

                await ctx.send(wishlist_message, reference=ctx.message)
            else:
                await ctx.send(f'Os "Interesses" de {member.display_name} estão vazios.', reference=ctx.message)
        else:
            await ctx.send(f'Os "Interesses" de {member.display_name} estão vazios.', reference=ctx.message)
    else:
        await ctx.send(f"{member.display_name} não está registrado. Use o comando `!registrar` para se registrar e criar uma Lista de Interesses.", reference=ctx.message)
    
@bot.command(name='negociar')
async def negociar(ctx, nome_do_jogador, usuario_alvo: discord.Member, valor_num: int, *lista):
    try:
        # Verifique se o usuário que chamou o comando tem uma organização
        if not get_organization(ctx, ctx.author.id):
            await ctx.send("Você não tem uma organização para negociar!", reference = ctx.message)
            return
        
        if not get_organization(ctx, usuario_alvo.id):
            await ctx.send(f"O usuário {usuario_alvo} não tem uma organização!", reference = ctx.message)
            return

        # Verifique se o usuário que chamou o comando é igual ao usuário alvo
        if ctx.author.id == usuario_alvo.id:
            await ctx.send("Você não pode negociar com você mesmo!", reference = ctx.message)
            return

        nome_do_jogador = nome_do_jogador.lower() 
        cursor.execute('SELECT * FROM allplayers WHERE name = ?', (nome_do_jogador,))
        player_data = cursor.fetchone()

        if player_data is None:
            await ctx.send(f"O jogador {nome_do_jogador} não foi encontrado no banco de dados.", reference = ctx.message)
            return
        
        if lista:
            for carta in lista:
                carta = carta.lower()
                cursor.execute('SELECT * FROM allplayers WHERE name = ?', (carta,))
                carta_data = cursor.fetchone()
            
                if carta_data is None:
                    await ctx.send(f"A carta {carta} não foi encontrada no banco de dados.", reference = ctx.message)
                    return

                if isOwner(ctx, carta, ctx.author.id) == False and isOwner(ctx, carta, usuario_alvo.id) == False:
                    await ctx.send(f"A carta {carta} não pertence a nenhum dos usuários.", reference = ctx.message)
                    return
            
        # Crie a mensagem de confirmação
        confirmation_message = f"Você está negociando {nome_do_jogador.upper()} com {usuario_alvo} por {valor_num} moedas"

        if lista:
            confirmation_message += f" e as seguintes cartas: {', '.join(lista.upper())}"

        confirmation_message += ". Tem certeza que deseja continuar?"

        # Envie a mensagem de confirmação
        confirm_msg = await ctx.send(confirmation_message, reference = ctx.message)

        # Adicione reações à mensagem de confirmação para permitir que os usuários confirmem ou cancelem a negociação
        await confirm_msg.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
        await confirm_msg.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

        # Função para verificar a reação
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
                if isOwner(ctx, nome_do_jogador, ctx.author.id):
                    await SellToPlayer(ctx, nome_do_jogador, usuario_alvo, valor_num, lista)
                elif isOwner(ctx, nome_do_jogador, usuario_alvo.id):
                    await BuyFromPlayer(ctx, nome_do_jogador, usuario_alvo, valor_num, lista)
                else:
                    await ctx.send("Nenhum dos usuários possui essa carta!", reference = ctx.message)
            else:
                await ctx.send("Negociação cancelada.")
        except asyncio.TimeoutError:
            pass
    except Exception as error:
        await ctx.send(f"Ocorreu um erro ao processar o comando. Detalhes do erro: {str(error)}", reference = ctx.message)

@negociar.error
async def negociar_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(title='Erro', description='Formato inválido. Use: !negociar [nome do jogador] [usuário alvo] [valor] [lista de cartas]', color=discord.Color.red())
        await ctx.send(embed=embed, reference = ctx.message)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(title='Erro', description='Argumento inválido. Verifique o formato dos argumentos.', color=discord.Color.red())
        await ctx.send(embed=embed, reference = ctx.message)

# Função para vender uma carta para outro jogador
async def SellToPlayer(ctx, nome_do_jogador, usuario_alvo: discord.Member, valor_num, lista):
    server_id = ctx.guild.id  

    # Verifique se o jogador existe no banco de dados
    cursor.execute('SELECT * FROM allplayers WHERE name = ?', (nome_do_jogador,))
    player_data = cursor.fetchone()

    cursor.execute('SELECT selling_max FROM organizations WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
    max = cursor.fetchone()

    id, name, overall, mec, dec, gak, twk, adp, ldr, price, nationality, league, team, position, photo_url, icon = player_data

    if valor_num > price * max[0]:
        embed = discord.Embed(
            title="Limite de Venda Excedido",
            description=f"O valor que você pediu {valor_num}, ultrapassa o seu limite de venda para a carta {name.upper()} \n O seu limite para essa carta: {price * max[0]} \n Para aumentar o limite visite a !loja",
            color=discord.Color.red()
            )
        await ctx.send(embed=embed)
        return

    # Crie um embed com a imagem do jogador
    player_photo_url = get_player_photo_url(nome_do_jogador)

    if player_photo_url:
        embed = discord.Embed(title=f"Negociação de {nome_do_jogador.upper()}")
        embed.set_image(url=player_photo_url)
        embed.add_field(name="Valor da Negociação", value=f"{valor_num} moedas", inline=False)
        embed.color = discord.Color.from_rgb(192, 192, 192)

        if lista:
            embed.add_field(name="Cartas em Negociação", value=', '.join(lista), inline=False)

        embed.set_author(name=bot_name, icon_url=bot_photo_url)
        embed.add_field(name ="", value= "Reaja com <:confirmar:1155491221863665666> para confirmar ou <:recusar:1155491252763107368> para cancelar a negociação.")
        
        # Envie o embed e aguarde a reação do usuário alvo
        message = await ctx.send(embed=embed,reference = ctx.message)
        await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
        await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

        # Função para verificar a reação do usuário alvo
        def check(reaction, user):
            return user == usuario_alvo and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
                # Atualiza o cofre na organização do usuário alvo e do autor
                cursor.execute('UPDATE organizations SET cofre = cofre + ? WHERE id = ? AND server_id = ?', (valor_num, ctx.author.id, server_id))
                connection.commit()
                cursor.execute('UPDATE organizations SET cofre = cofre - ? WHERE id = ? AND server_id = ?', (valor_num, usuario_alvo.id, server_id))
                connection.commit()

                # Atualiza a associação da carta à organização do usuário alvo no servidor atual
                cursor.execute('UPDATE organization_players SET org_id = ? WHERE server_id = ? AND player_id = ?', (usuario_alvo.id, server_id, player_data[0]))
                connection.commit()

                # Atualiza o contador de jogadores na organização do usuário alvo e do autor
                cursor.execute('UPDATE organizations SET player_count = player_count - 1 WHERE id = ? AND server_id = ?', (ctx.author.id,server_id))
                connection.commit()
                cursor.execute('UPDATE organizations SET player_count = player_count + 1 WHERE id = ? AND server_id = ?', (usuario_alvo.id, server_id))
                connection.commit()
                # Processa a lista de cartas em troca
                if lista:
                    for carta in lista:
                        # Verifica se a carta existe no banco de dados
                        cursor.execute('SELECT * FROM allplayers WHERE name = ?', (carta,))
                        carta_data = cursor.fetchone()
                        
                        # Atualiza a associação da carta à organização do usuário alvo
                        cursor.execute('UPDATE organization_players SET org_id = ? WHERE server_id = ? AND player_id = ?', (ctx.author.id, server_id, carta_data[0]))
                        connection.commit()
                        
                        # Atualiza o contador de jogadores na organização do usuário alvo e do autor
                        cursor.execute('UPDATE organizations SET player_count = player_count + 1 WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
                        connection.commit()
                        cursor.execute('UPDATE organizations SET player_count = player_count - 1 WHERE id = ? AND server_id = ?', (usuario_alvo.id, server_id))
                        connection.commit()

                await ctx.send(f"Negociação de {nome_do_jogador} com {usuario_alvo} foi confirmada.", reference = ctx.message)
            else:
                await ctx.send(f"Negociação de {nome_do_jogador} com {usuario_alvo} foi cancelada.", reference = ctx.message)
        except asyncio.TimeoutError:
            pass

# Função para comprar uma carta de outro jogador
async def BuyFromPlayer(ctx, nome_do_jogador, usuario_alvo: discord.Member, valor_num, lista):
    server_id = ctx.guild.id  
    # Verifique se o jogador existe no banco de dados
    cursor.execute('SELECT * FROM allplayers WHERE name = ?', (nome_do_jogador,))
    player_data = cursor.fetchone()

    cursor.execute('SELECT selling_max FROM organizations WHERE id = ? AND server_id = ?', (usuario_alvo.id, server_id))
    max = cursor.fetchone()

    id, name, overall, mec, dec, gak, twk, adp, ldr, price, nationality, league, team, position, photo_url, icon = player_data

    if valor_num > price * max[0]:
        embed = discord.Embed(
            title="Limite de Venda Excedido",
            description=f"O valor que você pediu {valor_num}, ultrapassa o seu limite de venda para a carta {name.upper()} de {usuario_alvo} \n O limite do usuário para essa carta: {price * max[0]}.",
            color=discord.Color.red()
            )
        await ctx.send(embed=embed)
        return

    # Crie um embed com a imagem do jogador
    player_photo_url = get_player_photo_url(nome_do_jogador)

    if player_photo_url:
        embed = discord.Embed(title=f"Compra de {nome_do_jogador}")
        embed.set_image(url=player_photo_url)
        embed.add_field(name="Valor da Compra", value=f"{valor_num} moedas", inline=False)
        embed.color = discord.Color.from_rgb(192, 192, 192)

        if lista:
            embed.add_field(name="Cartas em Troca", value=', '.join(lista), inline=False)

        embed.set_author(name=bot_name, icon_url=bot_photo_url)
        embed.add_field(name ="", value= "Reaja com <:confirmar:1155491221863665666> para confirmar ou <:recusar:1155491252763107368> para cancelar a negociação.")
        
        # Envie o embed e aguarde a reação do usuário alvo
        message = await ctx.send(embed=embed, reference = ctx.message)
        await message.add_reaction('<:confirmar:1155491221863665666>')  # Reação de confirmação (checkmark)
        await message.add_reaction('<:recusar:1155491252763107368>')  # Reação de cancelamento (X)

        # Função para verificar a reação do usuário alvo
        def check(reaction, user):
            return user == usuario_alvo and str(reaction.emoji) in ['<:confirmar:1155491221863665666>', '<:recusar:1155491252763107368>']

        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == '<:confirmar:1155491221863665666>':
                # Atualiza o cofre na organização do usuário alvo e do autor
                cursor.execute('UPDATE organizations SET cofre = cofre - ? WHERE id = ? AND server_id = ?', (valor_num, ctx.author.id, server_id))
                connection.commit()
                cursor.execute('UPDATE organizations SET cofre = cofre + ? WHERE id = ? AND server_id = ?', (valor_num, usuario_alvo.id, server_id))
                connection.commit()

                # Atualiza a associação da carta à organização do usuário alvo no servidor atual
                cursor.execute('UPDATE organization_players SET org_id = ? WHERE server_id = ? AND player_id = ?', (ctx.author.id, server_id, player_data[0]))
                connection.commit()

                # Atualiza o contador de jogadores na organização do usuário alvo e do autor
                cursor.execute('UPDATE organizations SET player_count = player_count + 1 WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
                connection.commit()
                cursor.execute('UPDATE organizations SET player_count = player_count - 1 WHERE id = ? AND server_id = ?', (usuario_alvo.id, server_id))
                connection.commit()
                # Processa a lista de cartas em troca
                if lista:
                    for carta in lista:
                        # Verifica se a carta existe no banco de dados
                        cursor.execute('SELECT * FROM allplayers WHERE name = ?', (carta,))
                        carta_data = cursor.fetchone()
                        
                        # Atualiza a associação da carta à organização do usuário alvo no servidor atual
                        cursor.execute('UPDATE organization_players SET org_id = ? WHERE server_id = ? AND player_id = ?', (usuario_alvo.id, server_id, carta_data[0]))
                        connection.commit()
                        
                        # Atualiza o contador de jogadores na organização do usuário alvo e do autor
                        cursor.execute('UPDATE organizations SET player_count = player_count - 1 WHERE id = ? AND server_id = ?', (ctx.author.id, server_id))
                        connection.commit()
                        cursor.execute('UPDATE organizations SET player_count = player_count + 1 WHERE id = ? AND server_id = ?', (usuario_alvo.id, server_id))
                        connection.commit()
                
                await ctx.send(f"Compra de {nome_do_jogador} de {usuario_alvo} foi confirmada." , reference = ctx.message)
            else:
                await ctx.send(f"Compra de {nome_do_jogador} de {usuario_alvo} foi cancelada." , reference = ctx.message)
        except asyncio.TimeoutError:
            pass

@bot.command(name='substituir',
    brief='Busca e exibe informações sobre um jogador.',
    help='Esse comando permite buscar um jogador pelo nome e exibir suas informações. '
    'Você deve fornecer o nome do jogador como argumento.',
    usage='!buscar_jogador [nome_do_jogador]')
async def buscar_jogador(ctx, *, nome_jogador):
    # Faça a busca na tabela allplayers usando o nome do jogador
    cursor.execute('SELECT name, nationality, team, position, league, photo_url, icon, price FROM allplayers WHERE name = ?', (nome_jogador,))
    jogador_info = cursor.fetchone()

    if jogador_info:
        # Se o jogador for encontrado, exiba suas informações
        name, nationality, team, position, league, photo_url, icon, price = jogador_info
        dono = await get_owner(ctx, name)

        # Construa um embed com as informações do jogador
        embed = discord.Embed(title=f'Informações do Jogador: {name}', color=discord.Color.blue())
        embed.add_field(name='Nacionalidade', value=nationality, inline=False)
        embed.add_field(name='Liga', value=league, inline=False)
        embed.add_field(name='Time', value=team, inline=False)
        embed.add_field(name='Posição', value=position, inline=False)
        embed.add_field(name='Preço', value=price, inline=False)
        embed.add_field(name='Dono', value=dono, inline=False)
        embed.set_image(url=photo_url)

        # Envie o embed para o canal
        message = await ctx.send(embed=embed)

        # Agora, peça ao usuário a nova URL para substituir a imagem do jogador
        await ctx.send(f"Por favor, forneça a nova URL da imagem que deseja usar para o jogador {name}. Digite 'cancelar' para cancelar a operação.")

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            resposta = await bot.wait_for('message', timeout=60, check=check)

            if resposta.content.lower() == 'cancelar':
                await ctx.send("Operação cancelada.")
            else:
                nova_url_imagem = resposta.content
                # Atualize a URL da imagem na tabela allplayers
                cursor.execute('UPDATE allplayers SET photo_url = ? WHERE name = ?', (nova_url_imagem, name))
                connection.commit()
                await ctx.send(f"URL da imagem para o jogador {name} atualizada com sucesso.")
        except asyncio.TimeoutError:
            await ctx.send("Tempo limite excedido. Operação cancelada.")
    else:
        await ctx.send(f"Jogador com o nome '{nome_jogador}' não encontrado.")

@bot.command(name='top', brief='Mostra os melhores jogadores por overall.')
async def top_players(ctx):
    try:
        cursor.execute('SELECT name, overall FROM allplayers ORDER BY overall DESC')  # Obtém todos os jogadores por overall
        top_players_data = cursor.fetchall()

        if not top_players_data:
            await ctx.send('Nenhum jogador encontrado na tabela allplayers.')
            return

        top_players_view = TopPlayersView(top_players_data)
        await top_players_view.start(ctx)
    except Exception as e:
        await ctx.send(f"Ocorreu um erro ao buscar os melhores jogadores: {str(e)}")


# Tarefa assíncrona para redefinir roll_count a cada roll_cooldown
@tasks.loop(minutes=30)  # Defina o intervalo de tempo desejado (em minutos)
async def reset_roll_count_task():
    cursor.execute('SELECT id FROM organizations')  # Consulta para obter todos os IDs de organizações
    organization_ids = cursor.fetchall()
    for org_id in organization_ids:
        reset_roll_count(org_id[0])  # O ID está na primeira posição da tupla

@tasks.loop(minutes=30)  # Defina o intervalo de tempo desejado (em minutos)
async def reset_claim_count_task():
    cursor.execute('SELECT id FROM organizations')  # Consulta para obter todos os IDs de organizações
    organization_ids = cursor.fetchall()
    for org_id in organization_ids:
        reset_claim_count(org_id[0])  # O ID está na primeira posição da tupla


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Comando não encontrado. Por favor, verifique o comando que você inseriu.")

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    reset_roll_count_task.start()
    reset_claim_count_task.start()

bot.run(TOKEN)