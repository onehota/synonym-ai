import json
import os
import re
import random
import difflib
import urllib.request
import urllib.parse
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ.get("8849657462:AAEw9eVqYk_pS5ubgzVNDKthQE8_1k_-8r0", "").strip()

PORT = int(os.environ.get("PORT", "10000"))

BASE_BRAIN_FILE = "brain.json"

WEBHOOK_PATH = "/telegram-webhook"


# ============================================================
# CHECK TOKEN
# ============================================================

if not BOT_TOKEN:
    print("❌ BOT_TOKEN غير موجود.")
    print("ضع BOT_TOKEN في Render Environment Variables.")


# ============================================================
# TELEGRAM API
# ============================================================

TELEGRAM_API = (
    "https://api.telegram.org/bot"
    + BOT_TOKEN
)


def telegram_api(method, data=None):

    if not BOT_TOKEN:
        return None

    url = TELEGRAM_API + "/" + method

    try:

        if data is None:
            data = {}

        encoded = urllib.parse.urlencode(
            data
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=encoded,
            method="POST"
        )

        request.add_header(
            "Content-Type",
            "application/x-www-form-urlencoded"
        )

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            raw = response.read().decode(
                "utf-8"
            )

        return json.loads(raw)

    except Exception as e:

        print(
            "Telegram API error:",
            e
        )

        return None


def send_message(chat_id, text):

    if not text:
        return

    # Telegram message limit
    max_length = 4000

    if len(text) <= max_length:

        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text
            }
        )

        return


    # تقسيم الرسائل الطويلة
    for i in range(
        0,
        len(text),
        max_length
    ):

        part = text[
            i:i + max_length
        ]

        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": part
            }
        )


# ============================================================
# ARABIC NORMALIZATION
# ============================================================

def normalize_ar(text):

    text = str(text).lower().strip()

    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text
    )

    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ٱ", "ا")

    text = text.replace("ى", "ي")
    text = text.replace("ؤ", "و")
    text = text.replace("ئ", "ي")
    text = text.replace("ة", "ه")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def tokenize(text):

    text = normalize_ar(text)

    return re.findall(
        r"[\w\u0600-\u06FF]+",
        text
    )


def sequence_similarity(a, b):

    a = normalize_ar(a)
    b = normalize_ar(b)

    if not a or not b:
        return 0.0

    return difflib.SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def token_similarity(a, b):

    ta = set(tokenize(a))
    tb = set(tokenize(b))

    if not ta or not tb:
        return 0.0

    return len(
        ta & tb
    ) / max(
        len(ta),
        len(tb)
    )


# ============================================================
# DEFAULT BRAIN
# ============================================================

def default_brain():

    return {

        "version": "Telegram-2.2",

        "groups": {},

        "memory": {

            "user": {},

            "facts": {},

            "preferences": {}

        },

        "learning": {

            "learned_items": 0,

            "total_replies": 0,

            "successful_replies": 0

        },

        "conversation": {

            "last_user": "",

            "last_ai": "",

            "history": []

        }

    }


# ============================================================
# SYNONYM AI
# ============================================================

class SynonymAI:

    def __init__(self):

        self.brain = default_brain()

        self.loaded_brain_files = []

        self.load_all_brains()


    # ========================================================
    # FIND ALL BRAIN FILES
    # ========================================================

    def find_brain_files(self):

        files = []

        try:

            for filename in os.listdir("."):

                if not os.path.isfile(
                    filename
                ):
                    continue

                lower = filename.lower()

                if re.fullmatch(
                    r"brain\d*\.json",
                    lower
                ):

                    files.append(
                        filename
                    )

        except Exception as e:

            print(
                "Brain scan error:",
                e
            )


        files.sort(
            key=lambda x: (
                0
                if x.lower() == "brain.json"
                else 1,
                x.lower()
            )
        )

        return files


    # ========================================================
    # STRUCTURE
    # ========================================================

    def ensure_structure(self, data):

        if not isinstance(
            data,
            dict
        ):

            return default_brain()


        base = default_brain()


        # groups
        groups = data.get(
            "groups",
            {}
        )

        if not isinstance(
            groups,
            dict
        ):

            groups = {}

        base["groups"] = groups


        # memory
        memory = data.get(
            "memory",
            {}
        )


        if isinstance(
            memory,
            list
        ):

            new_memory = {

                "user": {},

                "facts": {},

                "preferences": {}

            }


            for item in memory:

                if isinstance(
                    item,
                    dict
                ):

                    key = item.get(
                        "key"
                    )

                    value = item.get(
                        "value"
                    )

                    if key is not None:

                        new_memory[
                            "facts"
                        ][str(key)] = value


            memory = new_memory


        elif not isinstance(
            memory,
            dict
        ):

            memory = {

                "user": {},

                "facts": {},

                "preferences": {}

            }


        else:

            memory.setdefault(
                "user",
                {}
            )

            memory.setdefault(
                "facts",
                {}
            )

            memory.setdefault(
                "preferences",
                {}
            )


        base["memory"] = memory


        # learning
        learning = data.get(
            "learning",
            {}
        )

        if not isinstance(
            learning,
            dict
        ):

            learning = {}


        base["learning"][
            "learned_items"
        ] = learning.get(
            "learned_items",
            0
        )


        base["learning"][
            "total_replies"
        ] = learning.get(
            "total_replies",
            0
        )


        base["learning"][
            "successful_replies"
        ] = learning.get(
            "successful_replies",
            0
        )


        # conversation
        conversation = data.get(
            "conversation",
            {}
        )

        if not isinstance(
            conversation,
            dict
        ):

            conversation = {}


        base["conversation"][
            "last_user"
        ] = conversation.get(
            "last_user",
            ""
        )


        base["conversation"][
            "last_ai"
        ] = conversation.get(
            "last_ai",
            ""
        )


        history = conversation.get(
            "history",
            []
        )


        if not isinstance(
            history,
            list
        ):

            history = []


        base["conversation"][
            "history"
        ] = history


        return base


    # ========================================================
    # READ BRAIN FILE
    # ========================================================

    def read_brain_file(
        self,
        filename
    ):

        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)


            return self.ensure_structure(
                data
            )


        except Exception as e:

            print(
                "Cannot read",
                filename,
                e
            )

            return None


    # ========================================================
    # EXACT GROUP
    # ========================================================

    def find_exact_group(
        self,
        text
    ):

        target = normalize_ar(
            text
        )

        if not target:
            return None


        for gid, group in self.brain[
            "groups"
        ].items():

            for word in group.get(
                "words",
                []
            ):

                if normalize_ar(
                    word
                ) == target:

                    return gid


        return None


    # ========================================================
    # NEW GROUP ID
    # ========================================================

    def new_group_id(self):

        while True:

            gid = "g" + "".join(

                random.choice(
                    "abcdefghijklmnopqrstuvwxyz0123456789"
                )

                for _ in range(8)

            )

            if gid not in self.brain[
                "groups"
            ]:

                return gid


    # ========================================================
    # DEDUPLICATE
    # ========================================================

    def deduplicate_group(
        self,
        gid
    ):

        if gid not in self.brain[
            "groups"
        ]:

            return


        group = self.brain[
            "groups"
        ][gid]


        words = []

        seen = set()


        for word in group.get(
            "words",
            []
        ):

            word = str(
                word
            ).strip()

            key = normalize_ar(
                word
            )

            if key and key not in seen:

                seen.add(key)

                words.append(
                    word
                )


        answers = []

        seen = set()


        for answer in group.get(
            "answers",
            []
        ):

            answer = str(
                answer
            ).strip()

            key = normalize_ar(
                answer
            )

            if key and key not in seen:

                seen.add(key)

                answers.append(
                    answer
                )


        group["words"] = words

        group["answers"] = answers


    # ========================================================
    # MERGE GROUP
    # ========================================================

    def merge_group(
        self,
        incoming
    ):

        if not isinstance(
            incoming,
            dict
        ):

            return


        words = incoming.get(
            "words",
            []
        )

        answers = incoming.get(
            "answers",
            []
        )


        if not isinstance(
            words,
            list
        ):

            words = []


        if not isinstance(
            answers,
            list
        ):

            answers = []


        words = [
            str(x).strip()
            for x in words
            if str(x).strip()
        ]


        answers = [
            str(x).strip()
            for x in answers
            if str(x).strip()
        ]


        if not words:
            return


        existing_gid = None


        for word in words:

            existing_gid = (
                self.find_exact_group(
                    word
                )
            )

            if existing_gid:
                break


        # New group
        if existing_gid is None:

            gid = self.new_group_id()

            self.brain[
                "groups"
            ][gid] = {

                "words": words,

                "answers": answers,

                "usage": incoming.get(
                    "usage",
                    0
                ),

                "success": incoming.get(
                    "success",
                    0
                )

            }

            self.deduplicate_group(
                gid
            )

            return


        # Merge
        group = self.brain[
            "groups"
        ][existing_gid]


        group.setdefault(
            "words",
            []
        )

        group.setdefault(
            "answers",
            []
        )

        group.setdefault(
            "usage",
            0
        )

        group.setdefault(
            "success",
            0
        )


        for word in words:

            if normalize_ar(
                word
            ) not in [
                normalize_ar(x)
                for x in group["words"]
            ]:

                group[
                    "words"
                ].append(
                    word
                )


        for answer in answers:

            if normalize_ar(
                answer
            ) not in [
                normalize_ar(x)
                for x in group["answers"]
            ]:

                group[
                    "answers"
                ].append(
                    answer
                )


        group["usage"] += int(
            incoming.get(
                "usage",
                0
            ) or 0
        )


        group["success"] += int(
            incoming.get(
                "success",
                0
            ) or 0
        )


        self.deduplicate_group(
            existing_gid
        )


    # ========================================================
    # MERGE BRAIN
    # ========================================================

    def merge_brain(
        self,
        data
    ):

        groups = data.get(
            "groups",
            {}
        )


        if isinstance(
            groups,
            dict
        ):

            for group in groups.values():

                self.merge_group(
                    group
                )


        memory = data.get(
            "memory",
            {}
        )


        if isinstance(
            memory,
            dict
        ):

            for category in [
                "user",
                "facts",
                "preferences"
            ]:

                incoming = memory.get(
                    category,
                    {}
                )


                if not isinstance(
                    incoming,
                    dict
                ):

                    continue


                for key, value in incoming.items():

                    self.brain[
                        "memory"
                    ][category][
                        str(key)
                    ] = value


    # ========================================================
    # LOAD ALL BRAINS
    # ========================================================

    def load_all_brains(self):

        self.brain = default_brain()

        self.loaded_brain_files = []


        files = self.find_brain_files()


        for filename in files:

            data = self.read_brain_file(
                filename
            )


            if data is None:
                continue


            self.merge_brain(
                data
            )


            self.loaded_brain_files.append(
                filename
            )


        print(
            "Loaded brain files:",
            self.loaded_brain_files
        )


    # ========================================================
    # SAVE
    # ========================================================

    def save(self):

        temp = (
            BASE_BRAIN_FILE
            + ".tmp"
        )


        try:

            with open(
                temp,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.brain,
                    f,
                    ensure_ascii=False,
                    indent=2
                )


            os.replace(
                temp,
                BASE_BRAIN_FILE
            )


            return True


        except Exception as e:

            print(
                "Save error:",
                e
            )

            return False


    # ========================================================
    # SMART SEARCH
    # ========================================================

    def find_group(
        self,
        text
    ):

        target = normalize_ar(
            text
        )


        exact = self.find_exact_group(
            target
        )


        if exact:
            return exact


        best_gid = None

        best_score = 0.0


        target_tokens = tokenize(
            target
        )


        for gid, group in self.brain[
            "groups"
        ].items():

            for word in group.get(
                "words",
                []
            ):

                normalized_word = normalize_ar(
                    word
                )


                word_tokens = tokenize(
                    normalized_word
                )


                if (
                    len(target_tokens) == 1
                    and len(word_tokens) > 1
                ):

                    continue


                if (
                    len(target_tokens) > 1
                    and len(word_tokens) == 1
                    and target not in normalized_word
                ):

                    continue


                seq = sequence_similarity(
                    target,
                    normalized_word
                )


                tok = token_similarity(
                    target,
                    normalized_word
                )


                score = (
                    seq * 0.75
                    +
                    tok * 0.25
                )


                if score > best_score:

                    best_score = score

                    best_gid = gid


        if best_score >= 0.72:

            return best_gid


        return None


    # ========================================================
    # LEARN ANSWER
    # ========================================================

    def learn_answer(
        self,
        word,
        answer
    ):

        word = str(
            word
        ).strip()

        answer = str(
            answer
        ).strip()


        if not word or not answer:

            return (
                "⚠️ اكتب الكلمة والجواب."
            )


        gid = self.find_exact_group(
            word
        )


        if gid:

            group = self.brain[
                "groups"
            ][gid]


            if normalize_ar(
                answer
            ) not in [
                normalize_ar(x)
                for x in group.get(
                    "answers",
                    []
                )
            ]:

                group.setdefault(
                    "answers",
                    []
                ).append(
                    answer
                )


            self.deduplicate_group(
                gid
            )


            self.brain[
                "learning"
            ][
                "learned_items"
            ] += 1


            self.save()


            return (
                "✅ تم التعلم.\n"
                "🔑 الكلمات: "
                + ", ".join(
                    group["words"]
                )
                + "\n💬 الردود: "
                + ", ".join(
                    group["answers"]
                )
            )


        gid = self.new_group_id()


        self.brain[
            "groups"
        ][gid] = {

            "words": [
                word
            ],

            "answers": [
                answer
            ],

            "usage": 0,

            "success": 0

        }


        self.brain[
            "learning"
        ][
            "learned_items"
        ] += 1


        self.save()


        return (
            "✅ تم إنشاء معرفة جديدة.\n"
            f"🔑 {word}\n"
            f"💬 {answer}"
        )


    # ========================================================
    # LEARN SYNONYM
    # ========================================================

    def learn_synonym(
        self,
        word,
        synonym
    ):

        word = str(
            word
        ).strip()

        synonym = str(
            synonym
        ).strip()


        if not word or not synonym:

            return (
                "⚠️ اكتب الكلمة والمرادف."
            )


        gid_word = self.find_exact_group(
            word
        )

        gid_synonym = self.find_exact_group(
            synonym
        )


        # word exists
        if gid_word:

            group = self.brain[
                "groups"
            ][gid_word]


            if normalize_ar(
                synonym
            ) not in [
                normalize_ar(x)
                for x in group["words"]
            ]:

                group["words"].append(
                    synonym
                )


            self.deduplicate_group(
                gid_word
            )


            self.brain[
                "learning"
            ][
                "learned_items"
            ] += 1


            self.save()


            return (
                "✅ تم ربط المرادف.\n"
                "🔑 "
                + " ↔ ".join(
                    group["words"]
                )
            )


        # synonym exists
        if gid_synonym:

            group = self.brain[
                "groups"
            ][gid_synonym]


            if normalize_ar(
                word
            ) not in [
                normalize_ar(x)
                for x in group["words"]
            ]:

                group["words"].append(
                    word
                )


            self.deduplicate_group(
                gid_synonym
            )


            self.brain[
                "learning"
            ][
                "learned_items"
            ] += 1


            self.save()


            return (
                "✅ تم ربط الكلمتين.\n"
                "🔑 "
                + " ↔ ".join(
                    group["words"]
                )
            )


        # both new
        gid = self.new_group_id()


        self.brain[
            "groups"
        ][gid] = {

            "words": [
                word,
                synonym
            ],

            "answers": [],

            "usage": 0,

            "success": 0

        }


        self.brain[
            "learning"
        ][
            "learned_items"
        ] += 1


        self.save()


        return (
            "✅ تم إنشاء مجموعة مترادفات.\n"
            f"🔑 {word} ↔ {synonym}"
        )


    # ========================================================
    # MEMORY
    # ========================================================

    def remember(
        self,
        category,
        key,
        value
    ):

        if category not in self.brain[
            "memory"
        ]:

            category = "facts"


        self.brain[
            "memory"
        ][category][
            str(key)
        ] = value


        self.save()


    def show_memory(self):

        memory = self.brain[
            "memory"
        ]


        lines = [
            "🧠 ذاكرتي",
            "━━━━━━━━━━━━━━"
        ]


        for category in [
            "user",
            "facts",
            "preferences"
        ]:

            data = memory.get(
                category,
                {}
            )


            if not data:
                continue


            lines.append(
                "\n📂 " + category
            )


            for key, value in data.items():

                lines.append(
                    f"• {key}: {value}"
                )


        if len(lines) == 2:

            lines.append(
                "لا توجد معلومات محفوظة."
            )


        return "\n".join(
            lines
        )


    # ========================================================
    # GROUPS
    # ========================================================

    def show_groups(self):

        if not self.brain[
            "groups"
        ]:

            return (
                "📚 لا توجد مجموعات."
            )


        lines = [
            "📚 مجموعات المعرفة",
            "━━━━━━━━━━━━━━━━"
        ]


        for gid, group in self.brain[
            "groups"
        ].items():

            lines.append(
                "\n🔹 " + gid
            )


            lines.append(
                "🔑 "
                + ", ".join(
                    group.get(
                        "words",
                        []
                    )
                )
            )


            answers = group.get(
                "answers",
                []
            )


            if answers:

                lines.append(
                    "💬 "
                    + ", ".join(
                        answers
                    )
                )


        return "\n".join(
            lines
        )


    # ========================================================
    # STATS
    # ========================================================

    def statistics(self):

        groups = self.brain[
            "groups"
        ]


        words = 0

        answers = 0


        for group in groups.values():

            words += len(
                group.get(
                    "words",
                    []
                )
            )

            answers += len(
                group.get(
                    "answers",
                    []
                )
            )


        return (
            "📊 Synonym AI\n"
            "━━━━━━━━━━━━━━━━\n"
            f"🧠 ملفات brain: "
            f"{len(self.loaded_brain_files)}\n"
            f"📚 المجموعات: "
            f"{len(groups)}\n"
            f"🔑 الكلمات: "
            f"{words}\n"
            f"💬 الردود: "
            f"{answers}\n"
            f"📖 مرات التعلم: "
            f"{self.brain['learning']['learned_items']}\n\n"
            "📂 الملفات:\n"
            + "\n".join(
                "• " + x
                for x in self.loaded_brain_files
            )
        )


    # ========================================================
    # FORGET
    # ========================================================

    def forget_group(
        self,
        word
    ):

        gid = self.find_exact_group(
            word
        )


        if gid is None:

            return (
                f"⚠️ لم أجد معرفة لـ {word}"
            )


        group = self.brain[
            "groups"
        ][gid]


        words = ", ".join(
            group.get(
                "words",
                []
            )
        )


        del self.brain[
            "groups"
        ][gid]


        self.save()


        return (
            "🗑️ تم حذف:\n"
            + words
        )


    # ========================================================
    # UNKNOWN
    # ========================================================

    def unknown_response(
        self,
        text
    ):

        suggestions = []

        target = normalize_ar(
            text
        )


        for group in self.brain[
            "groups"
        ].values():

            for word in group.get(
                "words",
                []
            ):

                score = sequence_similarity(
                    target,
                    word
                )


                if score >= 0.55:

                    suggestions.append(
                        (
                            score,
                            word
                        )
                    )


        suggestions.sort(
            reverse=True
        )


        if suggestions:

            words = []

            for _, word in suggestions[:3]:

                if word not in words:

                    words.append(
                        word
                    )


            return (
                f"🤔 لا أعرف '{text}' بعد.\n\n"
                "هل تقصد:\n"
                + "\n".join(
                    "• " + x
                    for x in words
                )
                + "\n\n"
                "علمني:\n"
                f"تعلم {text} = الجواب"
            )


        return (
            f"🤔 لا أعرف '{text}' بعد.\n\n"
            "علمني:\n"
            f"تعلم {text} = الجواب"
        )


    # ========================================================
    # REPLY
    # ========================================================

    def reply(
        self,
        text
    ):

        original = str(
            text
        ).strip()


        if not original:

            return "..."


        txt = normalize_ar(
            original
        )


        # -----------------------------------------------
        # HELP
        # -----------------------------------------------

        if txt in [
            "مساعده",
            "مساعدة",
            "help",
            "/help"
        ]:

            return (
                "🤖 Synonym AI\n\n"
                "📚 التعلم:\n"
                "تعلم الكلمة = الجواب\n\n"
                "🔗 المرادف:\n"
                "تعلم الكلمة == المرادف\n\n"
                "🧠 الذاكرة:\n"
                "ذاكرتي\n\n"
                "📚 المجموعات:\n"
                "مجموعاتي\n\n"
                "📊 الإحصائيات:\n"
                "احصائيات\n\n"
                "🔄 إعادة فحص brain:\n"
                "تحديث\n\n"
                "🗑️ حذف:\n"
                "انسى الكلمة"
            )


        # -----------------------------------------------
        # UPDATE
        # -----------------------------------------------

        if txt in [
            "تحديث",
            "اعادة تحميل",
            "اعادة تحميل الذاكره",
            "تحديث الذاكره"
        ]:

            self.load_all_brains()


            return (
                "🔄 تم إعادة فحص ملفات brain.\n"
                f"🧠 عدد الملفات: "
                f"{len(self.loaded_brain_files)}"
            )


        # -----------------------------------------------
        # STATS
        # -----------------------------------------------

        if txt in [
            "احصائيات",
            "إحصائيات",
            "stats"
        ]:

            return self.statistics()


        # -----------------------------------------------
        # MEMORY
        # -----------------------------------------------

        if txt in [
            "ذاكرتي",
            "عقلي"
        ]:

            return self.show_memory()


        # -----------------------------------------------
        # GROUPS
        # -----------------------------------------------

        if txt in [
            "مجموعاتي",
            "مجموعات",
            "معرفتي"
        ]:

            return self.show_groups()


        # -----------------------------------------------
        # FORGET
        # -----------------------------------------------

        if txt.startswith(
            "انسى "
        ):

            word = original[
                len("انسى "):
            ].strip()


            return self.forget_group(
                word
            )


        # -----------------------------------------------
        # LEARN
        # -----------------------------------------------

        if txt.startswith(
            "تعلم"
        ):

            rest = original[
                len("تعلم"):
            ].strip()


            if "==" in rest:

                a, b = rest.split(
                    "==",
                    1
                )


                return self.learn_synonym(
                    a.strip(),
                    b.strip()
                )


            if "=" in rest:

                a, b = rest.split(
                    "=",
                    1
                )


                return self.learn_answer(
                    a.strip(),
                    b.strip()
                )


            return (
                "⚠️ الصيغة:\n\n"
                "تعلم الكلمة = الجواب\n\n"
                "أو:\n"
                "تعلم الكلمة == المرادف"
            )


        # -----------------------------------------------
        # MEMORY EXTRACTION
        # -----------------------------------------------

        m = re.match(
            r"^اسمي\s+(.+)$",
            txt
        )


        if m:

            name = m.group(
                1
            ).strip()


            self.remember(
                "user",
                "name",
                name
            )


            return (
                f"✅ حفظت أن اسمك {name}"
            )


        m = re.match(
            r"^عمري\s+(.+)$",
            txt
        )


        if m:

            age = m.group(
                1
            ).strip()


            self.remember(
                "user",
                "age",
                age
            )


            return (
                "✅ حفظت عمرك: "
                + age
            )


        m = re.match(
            r"^انا احب\s+(.+)$",
            txt
        )


        if m:

            thing = m.group(
                1
            ).strip()


            self.remember(
                "preferences",
                "likes",
                thing
            )


            return (
                "✅ حفظت أنك تحب "
                + thing
            )


        # -----------------------------------------------
        # SEARCH
        # -----------------------------------------------

        gid = self.find_group(
            original
        )


        if gid:

            group = self.brain[
                "groups"
            ][gid]


            group["usage"] = (
                group.get(
                    "usage",
                    0
                ) + 1
            )


            answers = group.get(
                "answers",
                []
            )


            if answers:

                answer = random.choice(
                    answers
                )


                self.brain[
                    "learning"
                ][
                    "total_replies"
                ] += 1


                self.brain[
                    "conversation"
                ][
                    "last_user"
                ] = original


                self.brain[
                    "conversation"
                ][
                    "last_ai"
                ] = answer


                self.brain[
                    "conversation"
                ][
                    "history"
                ].append({

                    "user": original,

                    "ai": answer

                })


                self.brain[
                    "conversation"
                ][
                    "history"
                ] = self.brain[
                    "conversation"
                ][
                    "history"
                ][-100:]


                self.save()


                return answer


        # -----------------------------------------------
        # UNKNOWN
        # -----------------------------------------------

        result = self.unknown_response(
            original
        )


        self.brain[
            "conversation"
        ][
            "last_user"
        ] = original


        self.brain[
            "conversation"
        ][
            "last_ai"
        ] = result


        self.save()


        return result


# ============================================================
# GLOBAL AI
# ============================================================

AI = SynonymAI()


# ============================================================
# TELEGRAM UPDATE
# ============================================================

def process_update(
    update
):

    try:

        message = update.get(
            "message"
        )


        if not message:
            return


        chat = message.get(
            "chat",
            {}
        )


        chat_id = chat.get(
            "id"
        )


        text = message.get(
            "text"
        )


        if chat_id is None:
            return


        if not text:

            send_message(
                chat_id,
                "⚠️ أرسل رسالة نصية."
            )

            return


        # /start
        if text.startswith(
            "/start"
        ):

            send_message(
                chat_id,
                "🤖 أهلاً بك في Synonym AI.\n\n"
                "اكتب «مساعدة» لمعرفة الأوامر."
            )

            return


        # /reload
        if text.startswith(
            "/reload"
        ):

            AI.load_all_brains()


            send_message(
                chat_id,
                "🔄 تمت إعادة فحص ملفات brain.\n"
                f"🧠 الملفات: "
                f"{len(AI.loaded_brain_files)}"
            )

            return


        result = AI.reply(
            text
        )


        send_message(
            chat_id,
            result
        )


    except Exception as e:

        print(
            "Update error:",
            e
        )


# ============================================================
# WEBHOOK
# ============================================================

class TelegramHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        if self.path == "/":

            data = (
                "Synonym AI is running."
            ).encode(
                "utf-8"
            )


            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.end_headers()

            self.wfile.write(
                data
            )

            return


        if self.path == "/health":

            data = b"OK"


            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain"
            )

            self.send_header(
                "Content-Length",
                "2"
            )

            self.end_headers()

            self.wfile.write(
                data
            )

            return


        self.send_response(
            404
        )

        self.end_headers()


    def do_POST(self):

        if self.path != WEBHOOK_PATH:

            self.send_response(
                404
            )

            self.end_headers()

            return


        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )


            body = self.rfile.read(
                length
            )


            update = json.loads(
                body.decode(
                    "utf-8"
                )
            )


            # نرسل الرد 200 بسرعة
            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain"
            )

            self.end_headers()

            self.wfile.write(
                b"OK"
            )


            # معالجة التحديث
            threading.Thread(
                target=process_update,
                args=(update,),
                daemon=True
            ).start()


        except Exception as e:

            print(
                "Webhook error:",
                e
            )


    def log_message(
        self,
        format,
        *args
    ):

        return


# ============================================================
# SET WEBHOOK
# ============================================================

def setup_webhook():

    external_url = os.environ.get(
        "RENDER_EXTERNAL_URL",
        ""
    ).strip()


    if not external_url:

        print(
            "⚠️ RENDER_EXTERNAL_URL غير موجود."
        )

        return


    webhook_url = (
        external_url
        + WEBHOOK_PATH
    )


    result = telegram_api(
        "setWebhook",
        {
            "url": webhook_url,

            "drop_pending_updates": "false"

        }
    )


    print(
        "Webhook:",
        webhook_url
    )


    print(
        "Telegram response:",
        result
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "================================"
    )

    print(
        "🤖 Synonym AI Telegram Bot"
    )

    print(
        "================================"
    )


    print(
        "🧠 Brain files:"
    )


    for filename in AI.loaded_brain_files:

        print(
            "   •",
            filename
        )


    setup_webhook()


    server = HTTPServer(
        (
            "0.0.0.0",
            PORT
        ),
        TelegramHandler
    )


    print(
        "🌐 Server running on port",
        PORT
    )


    server.serve_forever()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()