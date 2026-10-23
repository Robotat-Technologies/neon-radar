"""Spelling tables for the entity resolution benchmark (PHASE-2.md M2.9 deliverable 6).

Sources write one name many ways: Arabic names have no single romanisation (the article as
`Al-`, `Al `, `El-` or joined; Mohammed, Muhammad, Mohamed, Mohamad; the ʿAbd compounds joined
or split), and Russian and Ukrainian names follow several systems (BGN/PCGN, ICAO Doc 9303,
French-style émigré spellings, Ukrainian forms such as Oleksandr). The research note
`docs/research/2026-10-18/names-addresses.md` (sections 3.2, 3.3, 5.1, 5.2 and 5.4) describes
these conventions; the tables below hold a few of them. They are spelling conventions and
invented sounds, not people.

- `ARABIC_GIVEN`: given names from Faker's `ar_SA` list (marks removed) with Latin spellings;
  only names in both are drawn, so given names stay from Faker.
- `ARABIC_SURNAMES`: common occupational and place surnames, never a prominent family (Faker's
  `ar_SA` surnames are prominent families and are never used, ADR-0005), with `ARTICLE_FORMS`.
- `RUSSIAN_GIVEN`: given names from Faker's `ru_RU` list with Russian and Ukrainian Latin forms.
- `ROMANISATION` and `ENDINGS`: letter tables for Cyrillic surnames and patronymics, and the
  surname endings that sources spell differently (`-ov` and `-off`; `-sky`, `-ski`, `-skiy`).
- `SYLLABLES`: invented syllables with a Latin, an Arabic-script and a Cyrillic form; a listed
  or leaked person's surname joins two or three of them (deliverable 2).

Edit rules: as for `words.py`. After any change, regenerate the benchmark fixture and list the
new names for the Companies House check (OD-12).
"""

# Latin spellings of Arabic given names, keyed by the Arabic script without marks (tashkeel and
# shadda removed); the canonical spelling comes first.
ARABIC_GIVEN: dict[str, dict[str, tuple[str, ...]]] = {
    "male": {
        "محمد": ("Mohammed", "Muhammad", "Mohamed", "Mohamad"),
        "أحمد": ("Ahmed", "Ahmad"),
        "محمود": ("Mahmoud", "Mahmud"),
        "مصطفى": ("Mustafa", "Moustafa", "Mostafa"),
        "عبد الرحمن": ("Abdul Rahman", "Abdulrahman", "Abd al-Rahman", "Abdel Rahman"),
        "عبدالله": ("Abdullah", "Abdallah", "Abdulla"),
        "عبد العزيز": ("Abdul Aziz", "Abdulaziz", "Abd al-Aziz", "Abdelaziz"),
        "عبد الكريم": ("Abdul Karim", "Abdulkarim", "Abd al-Karim", "Abdelkarim"),
        "عبد الملك": ("Abdul Malik", "Abdulmalik", "Abd al-Malik", "Abdelmalek"),
        "عبد اللطيف": ("Abdul Latif", "Abdullatif", "Abd al-Latif", "Abdellatif"),
        "عبد الحكيم": ("Abdul Hakim", "Abdulhakim", "Abdelhakim"),
        "يوسف": ("Yusuf", "Youssef", "Yousef", "Yousif"),
        "حسين": ("Hussein", "Husain", "Hussain", "Husayn"),
        "حسن": ("Hassan", "Hasan"),
        "علي": ("Ali",),
        "عمر": ("Omar", "Umar"),
        "خالد": ("Khaled", "Khalid"),
        "سامي": ("Sami", "Samy"),
        "طارق": ("Tariq", "Tarek", "Tarik"),
        "كريم": ("Karim", "Kareem"),
        "نبيل": ("Nabil", "Nabeel"),
        "فيصل": ("Faisal", "Faysal", "Feisal"),
        "جمال": ("Jamal", "Gamal"),
        "جميل": ("Jamil", "Jameel", "Gamil"),
        "جعفر": ("Jaafar", "Jafar"),
        "حمزة": ("Hamza", "Hamzah"),
        "خليل": ("Khalil", "Khaleel"),
        "رشيد": ("Rashid", "Rachid", "Rasheed"),
        "سعيد": ("Saeed", "Said", "Saied"),
        "سليمان": ("Sulaiman", "Suleiman", "Soliman"),
        "صالح": ("Saleh", "Salih"),
        "عادل": ("Adel", "Adil"),
        "عثمان": ("Othman", "Osman", "Uthman"),
        "عماد": ("Imad", "Emad"),
        "فؤاد": ("Fouad", "Fuad"),
        "ماجد": ("Majed", "Majid"),
        "مازن": ("Mazen", "Mazin"),
        "مراد": ("Murad", "Mourad"),
        "منصور": ("Mansour", "Mansur"),
        "ناصر": ("Nasser", "Nasir"),
        "نزار": ("Nizar", "Nezar"),
        "هاني": ("Hani", "Hany"),
        "هاشم": ("Hashem", "Hashim"),
        "وليد": ("Walid", "Waleed"),
        "ياسر": ("Yasser", "Yasir"),
        "يحيى": ("Yahya", "Yehia"),
        "يونس": ("Younes", "Yunus", "Younis"),
        "زياد": ("Ziad", "Ziyad"),
        "رامي": ("Rami", "Ramy"),
        "فادي": ("Fadi", "Fady"),
        "سمير": ("Samir", "Sameer"),
        "عدنان": ("Adnan",),
        "غسان": ("Ghassan",),
        "فراس": ("Firas", "Feras"),
        "قاسم": ("Qasim", "Kassem", "Qassem"),
        "كمال": ("Kamal", "Kamel"),
        "مهدي": ("Mahdi", "Mehdi"),
        "موسى": ("Musa", "Moussa"),
        "نادر": ("Nader", "Nadir"),
        "وائل": ("Wael", "Wail"),
        "داوود": ("Dawood", "Daoud", "Dawud"),
        "صلاح الدين": ("Salah al-Din", "Salahuddin", "Salah Eddine", "Salaheddin"),
        "نور الدين": ("Nour al-Din", "Nureddin", "Noureddine", "Nuruddin"),
        "عز الدين": ("Izz al-Din", "Ezzeddine", "Izzeddin"),
    },
    "female": {
        "مريم": ("Maryam", "Mariam", "Meriem"),
        "هدى": ("Huda", "Hoda"),
        "هند": ("Hind", "Hend"),
        "ياسمين": ("Yasmin", "Yasmine", "Yasmeen"),
        "نوال": ("Nawal",),
        "دعاء": ("Doaa", "Duaa"),
        "ريم": ("Reem", "Rim"),
        "ريما": ("Rima", "Reema"),
        "لينا": ("Lina", "Leena"),
        "سجى": ("Saja", "Sajaa"),
        "شهد": ("Shahd", "Shahad"),
        "ضحى": ("Duha", "Doha"),
        "عالية": ("Alia", "Aliya", "Aaliyah"),
        "كوثر": ("Kawthar", "Kawther", "Kausar"),
        "هيام": ("Hiyam", "Hiam"),
        "وفاء": ("Wafaa", "Wafa"),
        "يسرى": ("Yusra", "Yousra", "Yosra"),
        "ابتسام": ("Ibtisam", "Ebtisam", "Ibtissam"),
        "ايمان": ("Iman", "Eman", "Imane"),
        "أحلام": ("Ahlam",),
        "أروى": ("Arwa",),
        "بشرى": ("Bushra", "Boushra"),
        "جميلة": ("Jamila", "Jameela", "Djamila"),
        "حياة": ("Hayat",),
        "ميسون": ("Maysoun", "Maisoon", "Mayssoun"),
        "نغم": ("Nagham",),
        "هناء": ("Hanaa", "Hana"),
        "زهرة": ("Zahra", "Zahraa"),
        "بثينة": ("Buthaina", "Bouthaina", "Buthayna"),
        "بتول": ("Batool", "Batoul"),
        "ناهد": ("Nahed", "Nahid"),
        "نوره": ("Noura", "Nora", "Nourah"),
        "هاجر": ("Hajar", "Hagar"),
        "جود": ("Joud", "Jood"),
    },
}

# (Arabic script without the article, Latin spellings): occupations and places of origin.
ARABIC_SURNAMES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("حداد", ("Haddad", "Hadad")), ("نجار", ("Najjar", "Naggar", "Najar")),
    ("خياط", ("Khayyat", "Khayat", "Khaiat")), ("عطار", ("Attar", "Atar")),
    ("صباغ", ("Sabbagh", "Sabagh")), ("حلاق", ("Hallaq", "Hallak")),
    ("قصاب", ("Qassab", "Kassab")), ("بيطار", ("Bitar", "Baytar", "Beitar")),
    ("طحان", ("Tahhan", "Tahan")), ("فران", ("Farran", "Faran")),
    ("حلبي", ("Halabi", "Halaby")), ("شامي", ("Shami", "Chami", "Shamy")),
    ("زيات", ("Zayyat", "Zayat")), ("نحاس", ("Nahhas", "Nahas")),
    ("صراف", ("Sarraf", "Saraf")), ("دباغ", ("Dabbagh", "Dabagh", "Debbagh")),
    ("صفار", ("Saffar", "Safar")), ("خباز", ("Khabbaz", "Khabaz")),
    ("حجار", ("Hajjar", "Hajar")), ("سماك", ("Sammak", "Samak")),
    ("مصري", ("Masri", "Masry", "Misri")), ("حمصي", ("Homsi", "Himsi")),
    ("حموي", ("Hamwi", "Hamawi")), ("كردي", ("Kurdi", "Kordi")),
    ("فاخوري", ("Fakhoury", "Fakhouri", "Fakhuri")), ("خوري", ("Khoury", "Khouri", "Khuri")),
    ("نقاش", ("Naqqash", "Nakkash")), ("سقا", ("Saqqa", "Sakka")),
    ("جزار", ("Jazzar", "Gazzar")),
)  # fmt: skip
ARABIC_ARTICLE = "ال"
# The article before a Latin surname: hyphenated, spaced, Egyptian `El-`, and joined.
ARTICLE_FORMS = ("Al-", "Al ", "El-", "Al")

# Cyrillic given name (as in Faker's ru_RU list) -> (Russian Latin forms, Ukrainian forms).
RUSSIAN_GIVEN: dict[str, dict[str, tuple[tuple[str, ...], tuple[str, ...]]]] = {
    "male": {
        "Александр": (("Aleksandr", "Alexander", "Alexandr"), ("Oleksandr",)),
        "Алексей": (("Aleksei", "Alexey", "Alexei", "Aleksey"), ("Oleksiy", "Oleksii")),
        "Анатолий": (("Anatoly", "Anatoliy", "Anatolii"), ()),
        "Андрей": (("Andrei", "Andrey"), ("Andriy", "Andrii")),
        "Аркадий": (("Arkady", "Arkadiy", "Arkadii"), ()),
        "Артем": (("Artem", "Artyom"), ()),
        "Богдан": (("Bogdan",), ("Bohdan",)),
        "Борис": (("Boris",), ("Borys",)),
        "Вадим": (("Vadim",), ("Vadym",)),
        "Валентин": (("Valentin",), ("Valentyn",)),
        "Валерий": (("Valery", "Valeriy", "Valerii"), ()),
        "Василий": (("Vasily", "Vasiliy", "Vassili"), ("Vasyl",)),
        "Виктор": (("Viktor", "Victor"), ()),
        "Виталий": (("Vitaly", "Vitaliy", "Vitalii"), ()),
        "Владимир": (("Vladimir", "Wladimir"), ("Volodymyr",)),
        "Владислав": (("Vladislav",), ("Vladyslav",)),
        "Всеволод": (("Vsevolod",), ()),
        "Вячеслав": (("Vyacheslav", "Viacheslav"), ()),
        "Геннадий": (("Gennady", "Gennadiy", "Gennadii"), ("Hennadiy",)),
        "Георгий": (("Georgy", "Georgiy", "Georgii"), ("Heorhiy",)),
        "Глеб": (("Gleb",), ("Hlib",)),
        "Григорий": (("Grigory", "Grigoriy", "Grigorii"), ("Hryhoriy",)),
        "Денис": (("Denis",), ("Denys",)),
        "Дмитрий": (("Dmitri", "Dmitry", "Dmitriy"), ("Dmytro",)),
        "Евгений": (("Evgeny", "Yevgeny", "Evgenii", "Evgeniy"), ("Yevhen",)),
        "Егор": (("Egor", "Yegor"), ("Yehor",)),
        "Иван": (("Ivan",), ()),
        "Игорь": (("Igor",), ("Ihor",)),
        "Илья": (("Ilya", "Ilia"), ("Illia",)),
        "Кирилл": (("Kirill",), ("Kyrylo",)),
        "Константин": (("Konstantin", "Constantin"), ("Kostiantyn", "Kostyantyn")),
        "Леонид": (("Leonid",), ()),
        "Максим": (("Maksim", "Maxim"), ("Maksym",)),
        "Матвей": (("Matvei", "Matvey"), ("Matviy",)),
        "Михаил": (("Mikhail", "Michail"), ("Mykhailo",)),
        "Никита": (("Nikita",), ("Mykyta",)),
        "Николай": (("Nikolai", "Nikolay"), ("Mykola",)),
        "Олег": (("Oleg",), ("Oleh",)),
        "Остап": (("Ostap",), ()),
        "Павел": (("Pavel",), ("Pavlo",)),
        "Петр": (("Pyotr", "Petr", "Piotr"), ("Petro",)),
        "Роман": (("Roman",), ()),
        "Ростислав": (("Rostislav",), ("Rostyslav",)),
        "Руслан": (("Ruslan",), ()),
        "Святослав": (("Svyatoslav", "Sviatoslav"), ()),
        "Семен": (("Semyon", "Semen", "Semion"), ()),
        "Сергей": (("Sergei", "Sergey", "Serguei"), ("Serhiy", "Serhii")),
        "Станислав": (("Stanislav",), ()),
        "Степан": (("Stepan",), ()),
        "Тарас": (("Taras",), ()),
        "Тимофей": (("Timofei", "Timofey"), ("Tymofiy",)),
        "Федор": (("Fyodor", "Fedor", "Feodor"), ("Fedir",)),
        "Юрий": (("Yuri", "Yury", "Yuriy", "Iurii"), ()),
        "Ярослав": (("Yaroslav", "Jaroslav"), ()),
    },
    "female": {
        "Анна": (("Anna",), ("Hanna",)),
        "Александра": (("Aleksandra", "Alexandra"), ("Oleksandra",)),
        "Алина": (("Alina",), ()),
        "Алла": (("Alla",), ()),
        "Анастасия": (("Anastasia", "Anastasiya", "Anastasiia"), ()),
        "Валентина": (("Valentina",), ("Valentyna",)),
        "Валерия": (("Valeria", "Valeriya", "Valeriia"), ()),
        "Вера": (("Vera",), ("Vira",)),
        "Вероника": (("Veronika", "Veronica"), ()),
        "Виктория": (("Viktoria", "Victoria", "Viktoriya"), ("Viktoriia",)),
        "Галина": (("Galina",), ("Halyna",)),
        "Дарья": (("Daria", "Darya"), ("Dariia",)),
        "Евгения": (("Evgenia", "Yevgenia", "Evgeniya"), ("Yevheniia",)),
        "Екатерина": (("Ekaterina", "Yekaterina"), ("Kateryna",)),
        "Елена": (("Elena", "Yelena"), ("Olena",)),
        "Елизавета": (("Elizaveta", "Yelizaveta"), ("Yelyzaveta",)),
        "Ирина": (("Irina",), ("Iryna",)),
        "Ксения": (("Ksenia", "Kseniya", "Xenia"), ("Kseniia",)),
        "Лариса": (("Larisa", "Larissa"), ("Larysa",)),
        "Людмила": (("Lyudmila", "Ludmila"), ("Liudmyla",)),
        "Маргарита": (("Margarita",), ("Marharyta",)),
        "Марина": (("Marina",), ("Maryna",)),
        "Мария": (("Maria", "Mariya"), ("Mariia",)),
        "Надежда": (("Nadezhda", "Nadejda"), ("Nadiia",)),
        "Наталья": (("Natalia", "Natalya", "Natalja"), ("Nataliia",)),
        "Нина": (("Nina",), ()),
        "Оксана": (("Oksana",), ()),
        "Ольга": (("Olga",), ("Olha",)),
        "Полина": (("Polina",), ()),
        "Светлана": (("Svetlana",), ("Svitlana",)),
        "София": (("Sofia", "Sofiya"), ("Sofiia",)),
        "Тамара": (("Tamara",), ()),
        "Татьяна": (("Tatiana", "Tatyana"), ("Tetiana", "Tetyana")),
        "Юлия": (("Yulia", "Yuliya", "Julia"), ("Yuliia",)),
    },
}

# Letter tables for Cyrillic surnames and patronymics: BGN/PCGN (the canonical spelling here),
# ICAO Doc 9303 (passports) and a French-style émigré spelling. Letters not listed are the same
# in all three. BGN/PCGN writes `е` as `ye` at the start of a word and after a vowel or sign.
_COMMON = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "з": "z", "и": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "ф": "f", "ы": "y",
    "ь": "", "ъ": "", "э": "e", "ж": "zh", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "у": "u", "е": "e",
}  # fmt: skip
ROMANISATION: dict[str, dict[str, str]] = {
    "bgn": _COMMON | {"ё": "yo", "й": "y", "ю": "yu", "я": "ya"},
    "icao": _COMMON | {"ё": "e", "й": "i", "ю": "iu", "я": "ia", "ъ": "ie"},
    "french": _COMMON | {
        "ё": "io", "й": "i", "ю": "iou", "я": "ia", "ж": "j", "ч": "tch", "ш": "ch",
        "щ": "chtch", "у": "ou",
    },
}  # fmt: skip
YE_AFTER = frozenset("аеёиоуыэюяьъ")
# Latin surname endings (after BGN/PCGN) and the other spellings sources use for them.
ENDINGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("skiy", ("sky", "ski")), ("skaya", ("skaia",)), ("ov", ("off",)), ("ev", ("eff",)),
    ("iy", ("y",)),
)  # fmt: skip

# Invented syllables: (Latin forms, Arabic script, Cyrillic). The first Latin form is canonical.
SYLLABLES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("kes",), "كيس", "кес"), (("tra",), "ترا", "тра"), (("ne",), "ني", "не"),
    (("bra",), "برا", "бра"), (("ske",), "سكي", "ске"), (("quil", "kwil"), "كويل", "квил"),
    (("lan",), "لان", "лан"), (("dro",), "درو", "дро"), (("vek", "wek"), "فيك", "век"),
    (("zar", "sar"), "زار", "зар"), (("mio",), "ميو", "мио"), (("tesh", "tesch"), "تيش", "теш"),
    (("kha", "ha"), "خا", "ха"), (("rud", "roud"), "رود", "руд"), (("vin", "win"), "فين", "вин"),
    (("os",), "وس", "ос"), (("pel",), "بيل", "пел"), (("dash", "dasch"), "داش", "даш"),
    (("rim",), "ريم", "рим"), (("tor",), "تور", "тор"), (("ul", "oul"), "ول", "ул"),
    (("gar", "ghar"), "غار", "гар"), (("fen",), "فن", "фен"), (("sol",), "سول", "сол"),
    (("mek", "mec"), "ميك", "мек"), (("ast",), "است", "аст"), (("ber",), "بير", "бер"),
    (("yun", "iun"), "يون", "юн"), (("zel", "sel"), "زيل", "зел"), (("dor",), "دور", "дор"),
    (("qan", "kan"), "قان", "кан"), (("lis",), "ليس", "лис"), (("thar", "tar"), "ثار", "тар"),
    (("mun", "moun"), "مون", "мун"), (("vosk", "wosk"), "فوسك", "воск"),
    (("ira",), "يرا", "ира"),
)  # fmt: skip
# Joins of the syllables above that are real surnames or read as one, and the spec's own
# examples (M2.9 reviews): an invented surname, or a typo of one, is redrawn when it is here.
NOT_INVENTED = (
    "Garvin", "Quillan", "Toros", "Khatra", "Voskos", "Kestra", "Torrud", "Dorfen", "Zelos",
    "Ostra", "Pelzar", "Ullan", "Traske", "Dorne", "Zelvin", "Selwin", "Selvin", "Rudvin",
    "Braske", "Vinkes", "Winkes", "Lanzar", "Sezar", "Tharos", "Taros", "Trazel", "Trasel",
    "Drovin", "Kestrane",
)  # fmt: skip
