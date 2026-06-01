"""
High-Retention Text Hooks Engine
Generates 15 scroll-stopping hooks optimized for Telegram mobile viewers.
Each hook is engineered with psychological triggers to freeze thumbs within 2 seconds.
"""

HIGH_RETENTION_HOOKS = [
    {
        "id": 1,
        "hook": "Your 'safe' 60/40 portfolio just silently lost 23% to inflation last year. Here's the allocation nobody on Wall Street will show you...",
        "trigger": "negative_velocity",
        "layout": "🔥 CONTRARIAN TRUTH\n\n{hook}\n\n👇 Tap for the breakdown"
    },
    {
        "id": 2,
        "hook": "I ran the numbers: If you started DCA into the S&P in January 2022, you're STILL underwater. But this one sector is up 340%...",
        "trigger": "curiosity_open_loop",
        "layout": "📊 THE REAL MATH\n\n{hook}\n\n🎯 The sector →"
    },
    {
        "id": 3,
        "hook": "Every AI stock you bought in 2024 is about to face this one regulatory ruling. The last time this happened, NVDA dropped 47% in 3 days.",
        "trigger": "fear_urgency",
        "layout": "⚠️ REGULATORY ALERT\n\n{hook}\n\n⏰ Time-sensitive read"
    },
    {
        "id": 4,
        "hook": "The Fed's next move isn't a rate cut. It's this. And every 'expert' on CNBC is getting it wrong...",
        "trigger": "authority_challenge",
        "layout": "🏛 FED WATCH\n\n{hook}\n\n💡 The real play →"
    },
    {
        "id": 5,
        "hook": "You think you're diversified? Check your brokerage. If you hold VOO, QQQ, and SCHD, you're 87% correlated to the same 7 stocks.",
        "trigger": "myth_debunk",
        "layout": "🎭 DIVERSIFICATION LIE\n\n{hook}\n\n🔍 The actual fix →"
    },
    {
        "id": 6,
        "hook": "I found a $2.3B pension fund that's 40% allocated to something your advisor legally can't recommend. The returns are...",
        "trigger": "forbidden_knowledge",
        "layout": "🔒 INSTITUTIONAL SECRET\n\n{hook}\n\n👁️ What they're holding →"
    },
    {
        "id": 7,
        "hook": "The last 3 times this yield curve inverted, this exact sector rallied 200%+ within 18 months. It's inverted again right now.",
        "trigger": "pattern_recognition",
        "layout": "📈 HISTORICAL PATTERN\n\n{hook}\n\n🎯 Sector play →"
    },
    {
        "id": 8,
        "hook": "Retail investors just pulled $14B from equity funds. The last time outflows hit this level? March 2009. The bottom.",
        "trigger": "contrarian_signal",
        "layout": "🩸 BLOOD IN THE STREETS\n\n{hook}\n\n💰 What to buy now →"
    },
    {
        "id": 9,
        "hook": "This country just made Bitcoin legal tender. Not El Salvador. Bigger. And their stock market is up 89% since the announcement.",
        "trigger": "surprise_reveal",
        "layout": "🌍 GLOBAL SHIFT\n\n{hook}\n\n🔗 Full analysis →"
    },
    {
        "id": 10,
        "hook": "Your broker's 'free' trades are costing you 2.3% annually in hidden spread arbitrage. Here's the math they buried in the fine print...",
        "trigger": "hidden_cost_exposure",
        "layout": "💸 THE HIDDEN FEE\n\n{hook}\n\n🧮 The real cost →"
    },
    {
        "id": 11,
        "hook": "One ETF holds 0.04% of AUM in this one derivative. If that position moves 10%, the NAV swings 23%. Nobody's talking about it.",
        "trigger": "risk_asymmetry",
        "layout": "⚡ LEVERAGE BOMB\n\n{hook}\n\n🚨 Ticker inside →"
    },
    {
        "id": 12,
        "hook": "I backtested every 'buy the dip' strategy since 1990. Only ONE approach beat buy-and-hold. It requires doing nothing for 11 months of the year...",
        "trigger": "counter_intuitive_method",
        "layout": "🧪 BACKTEST RESULTS\n\n{hook}\n\n📋 The strategy →"
    },
    {
        "id": 13,
        "hook": "The CEO of this Fortune 50 just sold $340M in stock. Their last 3 sales preceded -30%, -45%, and -62%. The ticker rhymes with 'META'.",
        "trigger": "insider_signal",
        "layout": "🚨 INSIDER ALERT\n\n{hook}\n\n📉 Historical chart →"
    },
    {
        "id": 14,
        "hook": "If your portfolio doesn't include exposure to this one geopolitical hedge, you're not investing. You're gambling. Here's why...",
        "trigger": "identity_challenge",
        "layout": "🛡️ PORTFOLIO INSURANCE\n\n{hook}\n\n🎯 The hedge →"
    },
    {
        "id": 15,
        "hook": "This AI company has $11B in revenue, 94% gross margins, and trades at 12x earnings. Wall Street covers it with 0 analysts. Here's why...",
        "trigger": "undiscovered_gem",
        "layout": "💎 THE HIDDEN GEM\n\n{hook}\n\n🔍 Ticker reveal →"
    }
]

def get_hook_by_trigger(trigger_type: str) -> list:
    """Get hooks filtered by psychological trigger type."""
    return [h for h in HIGH_RETENTION_HOOKS if h["trigger"] == trigger_type]

def format_hook_for_telegram(hook_data: dict, custom_cta: str = None) -> str:
    """Format a hook with its structural layout for Telegram posting."""
    layout = hook_data["layout"]
    formatted = layout.replace("{hook}", hook_data["hook"])
    if custom_cta:
        formatted += f"\n\n{custom_cta}"
    return formatted

def get_all_hooks_formatted() -> list:
    """Return all hooks formatted for immediate deployment."""
    return [format_hook_for_telegram(h) for h in HIGH_RETENTION_HOOKS]

def get_hook_by_id(hook_id: int) -> dict:
    """Get a specific hook by ID."""
    for hook in HIGH_RETENTION_HOOKS:
        if hook["id"] == hook_id:
            return hook
    return None

# Trigger types reference
TRIGGER_TYPES = [
    "negative_velocity",
    "curiosity_open_loop", 
    "fear_urgency",
    "authority_challenge",
    "myth_debunk",
    "forbidden_knowledge",
    "pattern_recognition",
    "contrarian_signal",
    "surprise_reveal",
    "hidden_cost_exposure",
    "risk_asymmetry",
    "counter_intuitive_method",
    "insider_signal",
    "identity_challenge",
    "undiscovered_gem"
]
