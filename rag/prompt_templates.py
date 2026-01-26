"""
Prompt Templates for Claude API interactions
"""

SYSTEM_PROMPT = """Eres un asesor financiero personal inteligente especializado en análisis de gastos y optimización de finanzas personales.

Tu rol es:
1. Analizar patrones de gasto del usuario
2. Identificar oportunidades de ahorro
3. Proporcionar recomendaciones prácticas y accionables
4. Comunicarte de forma clara, amigable pero profesional

Reglas:
- Siempre responde en español
- Usa números concretos cuando sea posible
- Sé constructivo, no crítico
- Prioriza sugerencias prácticas y realistas
- Si detectas algo preocupante, menciónalo de forma empática
- Evita jerga financiera compleja
- Mantén respuestas concisas pero completas"""


SPENDING_ANALYSIS_PROMPT = """Analiza los gastos del usuario basándote en el siguiente contexto financiero.

CONTEXTO FINANCIERO:
{context}

PATRONES DETECTADOS:
{patterns}

SOLICITUD DEL USUARIO:
{query}

Proporciona un análisis que incluya:
1. **Resumen General**: Estado actual de los gastos
2. **Patrones Identificados**: Tendencias positivas y áreas de atención
3. **Comparación**: Cómo se compara con períodos anteriores (si hay datos)
4. **Puntos Clave**: 3-5 observaciones más importantes

Formato tu respuesta de manera clara y estructurada."""


OPTIMIZATION_SUGGESTIONS_PROMPT = """Basándote en el análisis financiero del usuario, genera sugerencias de optimización.

DATOS DE GASTOS POR CATEGORÍA:
{category_data}

CONTEXTO HISTÓRICO:
{context}

METAS DEL USUARIO:
- Meta de ahorro por catorcena: ${savings_goal}
- Balance mínimo de confort: ${min_balance}

Genera sugerencias que incluyan:
1. **Categorías a Optimizar**: Cuáles tienen mayor potencial de ahorro
2. **Sugerencias Específicas**: Acciones concretas para cada categoría
3. **Ahorro Potencial**: Estimación de cuánto podría ahorrar
4. **Prioridad**: Ordenar de mayor a menor impacto

Sé realista y considera que algunos gastos son necesarios. No sugiereas reducir gastos esenciales de forma drástica."""


BEST_SAVINGS_TIME_PROMPT = """Analiza el mejor momento para que el usuario transfiera dinero a su cuenta de ahorros.

PATRÓN DE GASTOS POR DÍA DEL MES:
{daily_patterns}

OBLIGACIONES PENDIENTES:
{pending_obligations}

CALENDARIO DE INGRESOS:
- Primera catorcena: Día {first_paycheck}
- Segunda catorcena: Día {second_paycheck}

BALANCE ACTUAL:
- Cuenta de cheques: ${checking_balance}
- Meta de ahorro por catorcena: ${savings_goal}

Determina:
1. **Mejor Día**: Cuál es el día óptimo para transferir
2. **Razonamiento**: Por qué ese día es mejor
3. **Monto Seguro**: Cuánto puede transferir sin afectar obligaciones
4. **Alertas**: Si hay algún riesgo o consideración especial"""


CATEGORY_INSIGHT_PROMPT = """Proporciona un análisis detallado de la categoría de gastos especificada.

CATEGORÍA: {category}

DATOS DE LA CATEGORÍA:
{category_data}

HISTORIAL:
{history}

CONTEXTO GENERAL:
{context}

Incluye en tu análisis:
1. **Tendencia**: ¿Están aumentando, disminuyendo o estables?
2. **Comparación**: Vs promedio histórico
3. **Patrones**: Días/momentos de mayor gasto
4. **Recomendaciones**: Sugerencias específicas para esta categoría
5. **Meta Sugerida**: Un objetivo realista de gasto mensual"""


ANOMALY_EXPLANATION_PROMPT = """Explica las anomalías detectadas en los gastos del usuario.

ANOMALÍAS DETECTADAS:
{anomalies}

CONTEXTO HISTÓRICO:
{context}

Para cada anomalía:
1. **Descripción**: Qué fue lo inusual
2. **Contexto**: Comparación con el comportamiento normal
3. **Posible Causa**: Hipótesis de por qué ocurrió
4. **Recomendación**: Si requiere acción o es aceptable

Sé objetivo y no alarmista. Algunas anomalías pueden ser gastos legítimos únicos."""


CHAT_RESPONSE_PROMPT = """Responde la pregunta del usuario sobre sus finanzas personales.

PREGUNTA DEL USUARIO:
{message}

CONTEXTO FINANCIERO RELEVANTE:
{context}

HISTORIAL DE CONVERSACIÓN:
{conversation_history}

Instrucciones:
- Responde de forma directa y útil
- Si no tienes suficiente información, indícalo
- Sugiere preguntas de seguimiento si es apropiado
- Mantén un tono conversacional pero informativo"""


PATTERN_DETECTION_PROMPT = """Analiza los datos financieros y detecta patrones significativos.

DATOS DE GASTOS:
{expense_data}

PERÍODO ANALIZADO: {period}

Identifica:
1. **Tendencias de Gasto**: ¿Están aumentando o disminuyendo?
2. **Patrones Cíclicos**: ¿Hay gastos que se repiten?
3. **Anomalías**: ¿Hay gastos fuera de lo normal?
4. **Correlaciones**: ¿Hay relación entre categorías?

Responde en formato JSON con la siguiente estructura:
{
    "trends": [...],
    "cycles": [...],
    "anomalies": [...],
    "insights": [...]
}"""
