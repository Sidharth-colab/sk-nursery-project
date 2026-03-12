import database

plants = [
    ("China Doll (Large)", "Indoor", 250, 150),
    ("China Doll (Small)", "Indoor", 85, 45),
    ("Peace Lily", "Indoor", 260, 150),
    ("Money Plant", "Indoor", 50, 20),
    ("Snake Plant", "Indoor", 200, 90),
    ("Lucky Bamboo", "Indoor", 50, 20),
    ("Petunia (Large)", "Outdoor", 100, 45),
    ("Petunia (Small)", "Outdoor", 45, 20),
    ("Pichakam (Small)", "Outdoor", 40, 20),
    ("Nadan Chethi", "Outdoor", 120, 80),
    ("Bougainvillea (Small)", "Outdoor", 75, 45),
    ("Vinca (Winga)", "Outdoor", 35, 20),
    ("Kutti Mulla", "Outdoor", 40, 20),
    ("Pera (Guava)", "Outdoor", 80, 35),
    ("Coleus (Colis)", "Outdoor", 25, 10),
    ("Kanakambaram", "Outdoor", 25, 10),
    ("10-Mani", "Outdoor", 15, 5),
    ("Venda (Okra)", "Vegetable", 4, 1.5),
    ("Tomato", "Vegetable", 4, 1.5),
    ("Vazhuthananga (Brinjal)", "Vegetable", 4, 1.5),
    ("Kutti Kuramulak", "Vegetable", 90, 60),
]

database.create_database()

for name, category, price, cost in plants:
    database.add_new_plant(name, category, price, cost)
    print(f"✅ Added: {name}")

print("🌿 All plants added successfully!")
