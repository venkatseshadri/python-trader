import rule_engine
# Nested facts
facts = {'strategy': {'top_n': 5}}
rule = rule_engine.Rule('strategy.top_n == 5')
try:
    print(f"Match: {rule.matches(facts)}")
except Exception as e:
    print(f"Error: {e}")
