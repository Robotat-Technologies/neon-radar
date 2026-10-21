"""Hand-reviewed word lists for synthetic names and addresses (PHASE-1.md 7.1, M1.8e).

Rules for editing: neutral words only; no brands, listed companies or famous names; nothing
the wording lint forbids (contracts/wording/forbidden-terms.txt, for example "shell" or
"front"); never mimesis company lists (they are real companies). After any change, regenerate
the demo-mini fixture and check every new name against the Companies House search (OD-12).

People with names in several scripts use the curated spellings below, never a machine
transliteration (C1 R10). Arabic-script surnames come only from this list: Faker's `ar_SA`
surname list is mostly real, prominent families (ADR-0005).
"""

COMPANY_FIRST = (
    "Alder", "Amber", "Aspen", "Basalt", "Birch", "Bramble", "Briar", "Cobalt", "Copper",
    "Elder", "Fennel", "Flint", "Garnet", "Hazel", "Indigo", "Kestrel", "Larch", "Linnet",
    "Marram", "Myrtle", "Ochre", "Osier", "Plover", "Rowan", "Saffron", "Sorrel", "Tansy",
    "Teasel", "Umber", "Yarrow",
)  # fmt: skip
COMPANY_SECOND = (
    "Acre", "Beck", "Cairn", "Combe", "Croft", "Dell", "Fold", "Garth", "Gill", "Glade",
    "Holm", "Knoll", "Lea", "Mead", "Mere", "Moss", "Ness", "Quay", "Reach", "Scar", "Shaw",
    "Strand", "Tarn", "Thorpe", "Weald", "Wold",
)  # fmt: skip
COMPANY_ACTIVITY = (
    "Trading", "Logistics", "Supplies", "Consulting", "Services", "Holdings", "Ventures",
    "Foods", "Textiles", "Engineering", "Interiors", "Packaging", "Freight", "Catering",
)  # fmt: skip
AGENT_ACTIVITY = "Formations"
LENDER_ACTIVITY = "Finance"

# Arabic-script company names: "<noun> و<noun> <activity> <legal form>".
ARABIC_NOUNS = (
    "الصفصاف", "الكهرمان", "الزيزفون", "السنديان", "الريحان", "الخزامى", "القرنفل",
    "الفيروز", "المرمر", "العقيق", "الصنوبر", "اللوز",
)  # fmt: skip
ARABIC_ACTIVITY = ("للتجارة العامة", "للخدمات اللوجستية", "للاستشارات", "للتوريدات")

LEGAL_FORMS = {"gb": ("Ltd",), "vg": ("Limited",), "cy": ("Ltd",), "ae": ("ذ.م.م",)}
GB_PARTNERSHIP = "LLP"
# Every legal form `name_key` strips, also forms this generator never writes.
LEGAL_FORM_KEYS = (
    "ltd", "limited", "llp", "plc", "inc", "corp", "corporation", "llc", "fze", "fzco",
    "ооо", "ао", "зао", "пао", "ذ م م",
)  # fmt: skip

STREET_TYPES = ("Street", "Road", "Lane", "Row", "Walk", "Yard")
CITIES = {
    "gb": ("London", "Manchester", "Leeds", "Bristol", "Birmingham"),
    "vg": ("Road Town",),
    "cy": ("Limassol", "Nicosia"),
    "ae": ("Dubai",),
}
BANKS = ("Synthetic Bank One", "Synthetic Bank Two", "Synthetic Bank Three")

# (Latin, Arabic, Cyrillic) spellings.
ARABIC_GIVEN = {
    "male": (
        ("Omar", "عمر", "Омар"), ("Khaled", "خالد", "Халед"), ("Samir", "سمير", "Самир"),
        ("Tariq", "طارق", "Тарик"), ("Yousef", "يوسف", "Юсеф"), ("Karim", "كريم", "Карим"),
        ("Nabil", "نبيل", "Набиль"), ("Rami", "رامي", "Рами"), ("Fadi", "فادي", "Фади"),
        ("Bassam", "بسام", "Бассам"),
    ),
    "female": (
        ("Layla", "ليلى", "Лейла"), ("Rania", "رانيا", "Рания"), ("Huda", "هدى", "Худа"),
        ("Nadia", "نادية", "Надия"), ("Salma", "سلمى", "Сальма"), ("Dina", "دينا", "Дина"),
        ("Mona", "منى", "Мона"), ("Rana", "رنا", "Рана"),
    ),
}  # fmt: skip
# Common occupational and descriptive surnames, not tied to one prominent family.
ARABIC_SURNAMES = (
    ("Haddad", "حداد", "Хаддад"), ("Najjar", "نجار", "Наджар"), ("Khayyat", "خياط", "Хайят"),
    ("Attar", "عطار", "Аттар"), ("Sabbagh", "صباغ", "Саббаг"), ("Hallaq", "حلاق", "Халлак"),
    ("Qassab", "قصاب", "Кассаб"), ("Bitar", "بيطار", "Битар"), ("Tahhan", "طحان", "Таххан"),
    ("Farran", "فران", "Фарран"), ("Halabi", "حلبي", "Халаби"), ("Shami", "شامي", "Шами"),
    ("Jabbour", "جبور", "Джаббур"), ("Zayyat", "زيات", "Заят"),
)  # fmt: skip
# (Latin, Cyrillic). Surnames are the male form; the female form adds "a" / "а".
RUSSIAN_GIVEN = {
    "male": (("Ivan", "Иван"), ("Sergey", "Сергей"), ("Pavel", "Павел"), ("Oleg", "Олег"),
             ("Andrey", "Андрей"), ("Nikolay", "Николай")),
    "female": (("Irina", "Ирина"), ("Olga", "Ольга"), ("Natalia", "Наталья"),
               ("Elena", "Елена"), ("Marina", "Марина"), ("Tatiana", "Татьяна")),
}  # fmt: skip
RUSSIAN_SURNAMES = (
    ("Volkov", "Волков"), ("Sokolov", "Соколов"), ("Lebedev", "Лебедев"), ("Novikov", "Новиков"),
    ("Belov", "Белов"), ("Zaitsev", "Зайцев"), ("Golubev", "Голубев"), ("Komarov", "Комаров"),
)  # fmt: skip
