#!/usr/bin/env python3
"""
Database module for San Antonio MUD
Handles user authentication and data persistence
"""

import sqlite3
import hashlib
import os
import json
from datetime import datetime

class MUDDatabase:
    def __init__(self, db_path='samud.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                current_room TEXT DEFAULT 'alamo_plaza',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                exits TEXT DEFAULT '{}'
            )
        ''')

        # NPCs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npcs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                room_id TEXT NOT NULL,
                responses TEXT DEFAULT '{}',
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            )
        ''')

        # Items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                location_type TEXT NOT NULL,  -- 'room', 'player'
                location_id TEXT NOT NULL     -- room_id or user_id
            )
        ''')

        # Initialize rooms if they don't exist
        cursor.execute('SELECT COUNT(*) FROM rooms')
        if cursor.fetchone()[0] == 0:
            self.create_initial_rooms(cursor)

        # Initialize NPCs if they don't exist
        cursor.execute('SELECT COUNT(*) FROM npcs')
        if cursor.fetchone()[0] == 0:
            self.create_initial_npcs(cursor)

        # Initialize items if they don't exist
        cursor.execute('SELECT COUNT(*) FROM items')
        if cursor.fetchone()[0] == 0:
            self.create_initial_items(cursor)

        conn.commit()
        conn.close()
        print(f"Database initialized: {self.db_path}")

    def hash_password(self, password):
        """Hash a password with salt"""
        salt = os.urandom(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt + password_hash

    def verify_password(self, password, stored_hash):
        """Verify a password against stored hash"""
        salt = stored_hash[:32]
        stored_password_hash = stored_hash[32:]
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return password_hash == stored_password_hash

    def create_user(self, username, password):
        """Create a new user account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Username already exists"

            # Hash password and create user
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
            ''', (username, password_hash, datetime.now()))

            conn.commit()
            conn.close()
            return True, "Account created successfully"

        except sqlite3.Error as e:
            return False, f"Database error: {e}"

    def authenticate_user(self, username, password):
        """Authenticate a user login"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, password_hash FROM users WHERE username = ?
            ''', (username,))

            result = cursor.fetchone()
            if not result:
                conn.close()
                return False, "Invalid username or password"

            user_id, stored_hash = result

            if self.verify_password(password, stored_hash):
                # Update last login
                cursor.execute('''
                    UPDATE users SET last_login = ? WHERE id = ?
                ''', (datetime.now(), user_id))
                conn.commit()
                conn.close()
                return True, user_id
            else:
                conn.close()
                return False, "Invalid username or password"

        except sqlite3.Error as e:
            return False, f"Database error: {e}"

    def get_user_info(self, user_id):
        """Get user information by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT username, current_room FROM users WHERE id = ?
            ''', (user_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'username': result[0],
                    'current_room': result[1]
                }
            return None

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def update_user_room(self, user_id, room_id):
        """Update user's current room"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE users SET current_room = ? WHERE id = ?
            ''', (room_id, user_id))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

    def create_initial_rooms(self, cursor):
        """Create the initial San Antonio themed rooms"""
        rooms = [
            {
                'id': 'alamo_plaza',
                'name': 'The Alamo Plaza',
                'description': 'Stone walls surround you in this historic courtyard. Tourists move in and out, taking photos of the famous mission. The limestone facade of the Alamo Chapel stands solemnly to the north.',
                'exits': {'east': 'riverwalk_north', 'south': 'southtown'}
            },
            {
                'id': 'riverwalk_north',
                'name': 'River Walk North',
                'description': 'The water glistens as barges float past carrying tourists. Cafes line the banks with outdoor seating under colorful umbrellas. The sound of mariachi music drifts from nearby restaurants.',
                'exits': {'west': 'alamo_plaza', 'south': 'riverwalk_south', 'north': 'pearl'}
            },
            {
                'id': 'riverwalk_south',
                'name': 'River Walk South',
                'description': 'Cypress trees lean over the quiet waters here. Historic bridges arch overhead while paddleboats drift lazily by. Street vendors sell churros and cold drinks to passing visitors.',
                'exits': {'north': 'riverwalk_north', 'west': 'mission_san_jose'}
            },
            {
                'id': 'pearl',
                'name': 'The Pearl',
                'description': 'The old brewery has been transformed into a vibrant district. Families gather in the central plaza while live music echoes from the amphitheater. Artisan shops and restaurants fill the converted buildings.',
                'exits': {'south': 'riverwalk_north', 'east': 'tower_americas'}
            },
            {
                'id': 'tower_americas',
                'name': 'Tower of the Americas',
                'description': 'The 750-foot tower stretches high above the city skyline. Built for the 1968 World\'s Fair, it offers commanding views of San Antonio. The HemisFair Park spreads out below with its geometric walkways.',
                'exits': {'west': 'pearl'}
            },
            {
                'id': 'mission_san_jose',
                'name': 'Mission San Jose',
                'description': 'Known as the "Queen of the Missions," this 18th-century Spanish colonial church stands majestically. The Rose Window carved in limestone catches the light beautifully. Native American and Spanish cultures blend in the surrounding grounds.',
                'exits': {'east': 'riverwalk_south', 'north': 'southtown'}
            },
            {
                'id': 'southtown',
                'name': 'Southtown',
                'description': 'Colorful murals cover the walls of this artistic neighborhood. Hip cafes and galleries mix with traditional Mexican restaurants. The energy is young and creative, with street art around every corner.',
                'exits': {'north': 'alamo_plaza', 'south': 'mission_san_jose'}
            }
        ]

        for room in rooms:
            cursor.execute('''
                INSERT INTO rooms (id, name, description, exits)
                VALUES (?, ?, ?, ?)
            ''', (room['id'], room['name'], room['description'], json.dumps(room['exits'])))

        print("Initial rooms created")

    def get_room(self, room_id):
        """Get room information by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT name, description, exits FROM rooms WHERE id = ?
            ''', (room_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'id': room_id,
                    'name': result[0],
                    'description': result[1],
                    'exits': json.loads(result[2])
                }
            return None

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def get_users_in_room(self, room_id):
        """Get list of users currently in a room"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT username FROM users WHERE current_room = ?
            ''', (room_id,))

            results = cursor.fetchall()
            conn.close()

            return [result[0] for result in results]

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def create_initial_npcs(self, cursor):
        """Create the initial NPCs for San Antonio rooms"""
        npcs = [
            {
                'id': 'alamo_guide',
                'name': 'Maria, the Tour Guide',
                'description': 'A friendly woman in a park ranger uniform with a warm smile.',
                'room_id': 'alamo_plaza',
                'responses': {
                    'default': "Welcome to the Alamo! This sacred ground holds the memory of Texas heroes. Would you like to know about the history?",
                    'history': "In 1836, brave defenders including Davy Crockett and Jim Bowie made their last stand here. Remember the Alamo!",
                    'alamo': "The Alamo Chapel you see here is all that remains of the original mission. It's been carefully preserved since 1836.",
                    'texas': "Texas fought for independence from Mexico. The Battle of the Alamo was a pivotal moment in our history.",
                    'hello': "¡Hola! Welcome to San Antonio's most historic site!"
                }
            },
            {
                'id': 'mariachi_carlos',
                'name': 'Carlos, the Mariachi',
                'description': 'A cheerful musician in traditional charro outfit with a guitar slung over his shoulder.',
                'room_id': 'riverwalk_north',
                'responses': {
                    'default': "¡Buenas! I play music here every day. The River Walk comes alive with our songs!",
                    'music': "We play traditional Mexican music - rancheras, boleros, and corridos. Music is the soul of San Antonio!",
                    'guitar': "This guitar has been in my family for three generations. Every scratch tells a story.",
                    'song': "♪ La Llorona, la Llorona, de azul celeste ♪ - would you like to hear more?",
                    'riverwalk': "The River Walk is magical at night when all the lights reflect on the water. Perfect for serenades!"
                }
            },
            {
                'id': 'pearl_chef',
                'name': 'Chef Isabella',
                'description': 'An energetic chef with flour-dusted apron, carrying fresh ingredients from the farmers market.',
                'room_id': 'pearl',
                'responses': {
                    'default': "Welcome to The Pearl! This place has the best ingredients in all of San Antonio. Are you hungry?",
                    'food': "We have amazing tacos, barbacoa, puffy tacos - everything made with love and fresh ingredients!",
                    'tacos': "Puffy tacos are a San Antonio specialty! The shells are fried fresh and puffed up like little pillows.",
                    'pearl': "This used to be a brewery, now it's a food paradise! Local farmers bring their best produce here.",
                    'cooking': "The secret to good Mexican food is fresh ingredients and cooking with your heart, not just your hands."
                }
            },
            {
                'id': 'mission_padre',
                'name': 'Father Miguel',
                'description': 'An elderly priest in brown robes, tending to the mission gardens with gentle care.',
                'room_id': 'mission_san_jose',
                'responses': {
                    'default': "Peace be with you, my child. Mission San José has welcomed visitors for over 250 years.",
                    'mission': "This is the Queen of Missions, built in 1720. We've preserved the faith and culture of our ancestors.",
                    'rose': "Ah, the Rose Window! Carved by Pedro Huizar for his beloved Rosa. Love and devotion made eternal in stone.",
                    'god': "God's house is always open. Here, Spanish and indigenous cultures learned to live as one.",
                    'peace': "In these walls, you'll find peace that has lasted centuries. Take a moment to reflect."
                }
            },
            {
                'id': 'street_artist',
                'name': 'Diego, the Muralist',
                'description': 'A young artist with paint-stained hands, working on a colorful mural depicting local culture.',
                'room_id': 'southtown',
                'responses': {
                    'default': "¡Órale! You like the murals? Southtown is where San Antonio's artistic soul lives and breathes.",
                    'art': "Every wall here tells a story - our history, our dreams, our struggles. Art is how we speak our truth.",
                    'mural': "This one shows the blending of cultures - Mexican, Native American, and Texan. We're all mixed together here.",
                    'culture': "San Antonio is a mestizo city - mixed heritage, mixed flavors, mixed dreams. That's what makes us beautiful.",
                    'southtown': "This neighborhood is gentrifying fast, but we're fighting to keep our cultura alive through art."
                }
            }
        ]

        for npc in npcs:
            cursor.execute('''
                INSERT INTO npcs (id, name, description, room_id, responses)
                VALUES (?, ?, ?, ?, ?)
            ''', (npc['id'], npc['name'], npc['description'], npc['room_id'], json.dumps(npc['responses'])))

        print("Initial NPCs created")

    def get_npcs_in_room(self, room_id):
        """Get list of NPCs in a room"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, description, responses FROM npcs WHERE room_id = ?
            ''', (room_id,))

            results = cursor.fetchall()
            conn.close()

            npcs = []
            for result in results:
                npcs.append({
                    'id': result[0],
                    'name': result[1],
                    'description': result[2],
                    'responses': json.loads(result[3])
                })

            return npcs

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def get_npc(self, npc_id):
        """Get NPC by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT name, description, room_id, responses FROM npcs WHERE id = ?
            ''', (npc_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'id': npc_id,
                    'name': result[0],
                    'description': result[1],
                    'room_id': result[2],
                    'responses': json.loads(result[3])
                }
            return None

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None

    def create_initial_items(self, cursor):
        """Create the initial items for San Antonio rooms"""
        items = [
            {
                'id': 'alamo_brochure',
                'name': 'a historic brochure',
                'description': 'A colorful brochure about the Battle of the Alamo with pictures of the heroes.',
                'location_type': 'room',
                'location_id': 'alamo_plaza'
            },
            {
                'id': 'guitar_pick',
                'name': 'a tortoiseshell guitar pick',
                'description': 'A well-worn guitar pick made of tortoiseshell, dropped by a mariachi musician.',
                'location_type': 'room',
                'location_id': 'riverwalk_north'
            },
            {
                'id': 'churros',
                'name': 'fresh churros',
                'description': 'Warm, crispy churros dusted with cinnamon sugar. They smell heavenly.',
                'location_type': 'room',
                'location_id': 'riverwalk_south'
            },
            {
                'id': 'recipe_card',
                'name': 'a handwritten recipe card',
                'description': 'A stained index card with a recipe for "Abuela\'s Perfect Puffy Tacos" in elegant cursive.',
                'location_type': 'room',
                'location_id': 'pearl'
            },
            {
                'id': 'mission_bell',
                'name': 'a small mission bell',
                'description': 'A tiny brass bell replica of those that once called the faithful to prayer.',
                'location_type': 'room',
                'location_id': 'mission_san_jose'
            },
            {
                'id': 'paint_brush',
                'name': 'a paint-stained brush',
                'description': 'An artist\'s brush with dried acrylic paint in vibrant colors of red, blue, and yellow.',
                'location_type': 'room',
                'location_id': 'southtown'
            },
            {
                'id': 'tower_postcard',
                'name': 'a vintage postcard',
                'description': 'A postcard from the 1968 World\'s Fair showing the Tower of the Americas in its full glory.',
                'location_type': 'room',
                'location_id': 'tower_americas'
            }
        ]

        for item in items:
            cursor.execute('''
                INSERT INTO items (id, name, description, location_type, location_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (item['id'], item['name'], item['description'], item['location_type'], item['location_id']))

        print("Initial items created")

    def get_items_in_room(self, room_id):
        """Get list of items in a room"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, description FROM items
                WHERE location_type = 'room' AND location_id = ?
            ''', (room_id,))

            results = cursor.fetchall()
            conn.close()

            items = []
            for result in results:
                items.append({
                    'id': result[0],
                    'name': result[1],
                    'description': result[2]
                })

            return items

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def get_player_items(self, user_id):
        """Get list of items carried by a player"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, description FROM items
                WHERE location_type = 'player' AND location_id = ?
            ''', (str(user_id),))

            results = cursor.fetchall()
            conn.close()

            items = []
            for result in results:
                items.append({
                    'id': result[0],
                    'name': result[1],
                    'description': result[2]
                })

            return items

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return []

    def move_item(self, item_id, new_location_type, new_location_id):
        """Move an item to a new location"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE items SET location_type = ?, location_id = ? WHERE id = ?
            ''', (new_location_type, str(new_location_id), item_id))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

    def get_item(self, item_id):
        """Get item by ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT name, description, location_type, location_id FROM items WHERE id = ?
            ''', (item_id,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'id': item_id,
                    'name': result[0],
                    'description': result[1],
                    'location_type': result[2],
                    'location_id': result[3]
                }
            return None

        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return None