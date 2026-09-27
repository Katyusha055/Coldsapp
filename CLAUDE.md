# Coldsapp — contexto para Claude Code

CRM SaaS multi-tenant que automatiza notificaciones de WhatsApp y gestión de clientes para talleres de reparación pequeños (electrónica, electrodomésticos, PCs) en Ecuador y Latinoamérica. Desarrollo solo, part-time.

**Filosofía del producto:** construir solo la capa de automatización de WhatsApp (el diferenciador real). Todo lo demás se integra, no se construye: inventario vía InvenTree/Inventoros, facturación electrónica vía Datil/Facturero. Sin integración directa al SRI, sin builds custom de cosas ya resueltas.

## Stack

- **Backend:** FastAPI + PostgreSQL. Sin ORM — SQL directo con `psycopg`. Migraciones con Alembic (reemplazando un `schema.py` + `init_db.py` legacy). Tests con `pytest` + `mutmut` (mutation testing).
- **Frontend:** Vue.js 3 + PrimeVue (tema Aura, azul) + Pinia.
- **WhatsApp:** Evolution API v2.3.7 (basada en Baileys). Ver "Decisión: Evolution API" abajo — no sugerir migrar a la API oficial de Meta sin que se pida explícitamente.
- **IA:** OpenRouter, modelos baratos, solo para generar variantes de copy (spintax) en broadcasts. No es un feature decorativo — el propósito es la no-determinación del texto, no "usar IA".
- **Deploy:** Railway + Docker.

## Arquitectura

Patrón estricto **Router → Service → Repository** por carpeta de feature.

- Solo las funciones de **repository** reciben `conn` (la conexión a DB).
- El **service** abre sus propias conexiones; no recibe `conn` desde el router.
- El **router** extrae `user_id` del JWT vía `CurrentUser` y le pasa al service *solo eso* — nunca el request completo ni el token crudo.
- Dentro del service, separar funciones puras de I/O cuando sea razonable (ej. `_filter_contacts`, `_filter_chats`, `_reconcile`) para poder testearlas sin mocks. Es el patrón ya usado en el feature de contactos — replicarlo, no reinventar otro.

**Multi-tenancy:** todo dato de negocio está scoped por tenant/usuario. Pinia stores usan patrón cache-once-invalidate-on-mutation. Nunca `localStorage` para datos de cliente (riesgo XSS). Bug conocido y ya identificado: el flag `loaded` de un store no se reseteaba en logout, filtrando datos entre tenants — el fix es `$reset()` en logout. Si tocás stores, verificar que este patrón esté aplicado en cualquier store nuevo.

## Decisiones de diseño ya cerradas (no re-litigar)

**Evolution API (no oficial) en vez de la API oficial de WhatsApp Business:**
La API oficial de Meta/Twilio se investigó y se descartó — exige verificación de negocio con matching exacto de documentos legales (RUC vs. nombre comercial), algo que la mayoría de talleres informales del segmento no puede cumplir. Evolution API es la única vía viable para este segmento y fase. Es una violación conocida de los ToS de WhatsApp Business, aceptada conscientemente como riesgo de negocio para la fase de validación temprana, con migración a la API oficial en el roadmap cuando el volumen del cliente lo justifique. No es ignorancia ni negación — es una decisión documentada. No proponer "usar la API oficial" como solución a un bug o feature sin que se pida.

**Riesgo de ban de WhatsApp — mitigación, no evasión:**
El spintax (variación de mensajes) y el rate limiting existen para no reproducir un patrón de comportamiento que WhatsApp ya castiga (texto idéntico a muchos destinatarios en poco tiempo), incluso en usuarios humanos que copian y pegan manualmente — hay casos documentados. No es "evadir detección", es comportarse como lo haría el dueño real del negocio usando WhatsApp a mano. El diseño mitiga solo contactos que ya escribieron primero o están guardados — nunca números fríos. El evento de bloqueo masivo de WhatsApp del 3 de agosto de 2026 (confirmado por Meta como falso positivo) estableció que el riesgo de ban es sistémico de la plataforma, no exclusivo de herramientas no oficiales — así se comunica a los clientes.

**Reconciliación de contactos (Feature 1):**
`findContacts` + `findChats` se reconcilian en un solo paso con `asyncio.gather`. Los identificadores `@lid` son una feature de privacidad de WhatsApp — se resuelven vía `remoteJidAlt` en `lastMessage.key`; solo números `@s.whatsapp.net` resueltos entran a la DB, nunca `@lid` crudo. `NULL` se persiste para nombres faltantes; el placeholder "Sin Nombre" se aplica solo en la capa de lectura del frontend, nunca en DB. El upsert usa `ON CONFLICT DO UPDATE ... WHERE EXCLUDED.name IS NOT NULL AND != ''` para evitar que el bug de `pushName` pise nombres ya limpios — cualquier lógica nueva de escritura de `name` debe respetar esta misma regla de "nunca pisar un nombre ya puesto". El contacto de sistema `0@s.whatsapp.net` se filtra siempre.

**Contactos vs. Clientes:** son dominios separados, sin vinculación automática. No asumir que un contacto de WhatsApp es un cliente del CRM sin que exista ese link explícito.

**Borrado:** no hay endpoint DELETE para contactos — el flag `opted_out` cubre el "ocultar"; un hard delete sería deshecho por la próxima reconciliación con Evolution API.

## Cómo correr / testear

_(completar con los comandos reales — no inferidos: `docker compose up`, comando de tests, comando de migraciones Alembic, variables de entorno mínimas para levantar local)_

## Convenciones

- Preferencia de estilo: directo, sin over-engineering, sin verbosidad. Empujar de vuelta si una propuesta es más compleja de lo que la fase requiere, o si el análisis se exagera.
- Validación empírica antes de decidir arquitectura: probar el comportamiento real de la API (Evolution API, etc.) contra datos vivos antes de fijar decisiones de diseño.
- Alinear versiones de dependencias entre dev y prod explícitamente — un mismatch de versión de Evolution API (v2.1.1 vs v2.3.7) ya causó una diferencia silenciosa en el shape de las respuestas que parecía pérdida de datos.
 
IMPORTANTE: Aunque el documento este en español, siempre responde en ingles si el usuario te habla en ingles, y si te habla en español, respondes en español. 