# Sistema de Chat PipeWise

## Descripción General

El sistema de chat de PipeWise es una interfaz conversacional avanzada que integra la AI SDK de Vercel con los agentes de inteligencia artificial del backend. Proporciona una experiencia de usuario intuitiva para interactuar con las funcionalidades de calificación de leads, programación de reuniones y gestión de contactos.

## Características Principales

### 🎯 Interfaz Centrada
- **Estado Inicial**: El campo de entrada aparece centrado en la página al cargar
- **Transición Fluida**: Una vez que se envía el primer mensaje, se mueve al fondo de la página
- **Responsivo**: Adaptable a diferentes tamaños de pantalla

### 🤖 Integración con Agentes AI
- **OpenAI GPT-4o**: Modelo principal para conversaciones naturales
- **Tools Integration**: Conecta con herramientas específicas de PipeWise
- **Streaming**: Respuestas en tiempo real con indicadores de escritura

### 🔧 Herramientas Disponibles
1. **analyze_lead**: Analiza información de leads y estado de calificación
2. **schedule_meeting**: Programa reuniones con leads
3. **send_email**: Envía emails personalizados a prospectos
4. **twitter_dm**: Envía mensajes directos en Twitter

### 🎨 Componentes UI
- **PromptBox**: Campo de entrada avanzado con herramientas
- **ChatBubble**: Burbujas de mensajes estilizadas
- **AgentPlan**: Visualización del workflow de agentes
- **TextShimmer**: Animaciones de carga y procesamiento

## Estructura de Archivos

```
frontend/
├── app/
│   ├── chat/
│   │   └── page.tsx                 # Página principal del chat
│   └── api/
│       └── chat/
│           └── route.ts             # API endpoint para el chat
├── components/
│   ├── ui/
│   │   ├── prompt-box.tsx           # Componente de entrada principal
│   │   ├── chat-bubble.tsx          # Burbujas de mensajes
│   │   ├── agent-plan.tsx           # Visualizador de workflows
│   │   ├── text-shimmer.tsx         # Animaciones de texto
│   │   └── message-loading.tsx      # Indicador de carga
│   └── app-sidebar.tsx              # Navegación actualizada
└── docs/
    └── CHAT_SYSTEM.md               # Esta documentación
```

## Instalación y Configuración

### 1. Dependencias Requeridas

```bash
cd frontend
npm install framer-motion @radix-ui/react-popover ai @ai-sdk/openai
```

### 2. Variables de Entorno

Agregar al archivo `.env.local`:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# PipeWise Backend (opcional)
PIPEWISE_BACKEND_URL=http://localhost:8000

# Opciones adicionales
USE_PIPEWISE_BACKEND=true
```

### 3. Iniciar el Servidor

```bash
npm run dev
```

## Uso del Sistema

### Navegación
1. Accede a la pestaña **"Chat"** desde el sidebar
2. La interfaz se carga con el prompt centrado
3. Escribe tu mensaje y presiona Enter o haz clic en el botón de envío

### Comandos y Capacidades

#### Análisis de Leads
```
"Analiza este lead: Juan Pérez, CEO de TechCorp, interesado en automatización"
```

#### Programación de Reuniones
```
"Programa una reunión con juan@techcorp.com para una demo del producto"
```

#### Envío de Emails
```
"Envía un email de seguimiento a maria@startup.com sobre nuestra propuesta"
```

#### Twitter Outreach
```
"Envía un DM a @target_user sobre nuestros servicios"
```

### Workflow de Agentes
- Cuando se activan herramientas, aparece un panel lateral derecho
- Muestra el progreso del workflow en tiempo real
- Visualiza qué agente está activo y las tareas en ejecución

## Componentes Técnicos

### PromptBox
El componente principal de entrada incluye:
- **Auto-resize**: Se ajusta automáticamente al contenido
- **Tool Selection**: Popover para seleccionar herramientas específicas
- **File Attachment**: Soporte para adjuntar imágenes
- **Voice Recording**: Botón para grabación de voz (preparado para futuras funcionalidades)

```typescript
interface PromptBoxProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  onSubmit?: (message: string, options?: { tools?: string[] }) => void;
}
```

### API Route
El endpoint `/api/chat` maneja:
- **Streaming Responses**: Usando la AI SDK de Vercel
- **Tool Calling**: Integración con funciones específicas
- **Error Handling**: Manejo robusto de errores
- **Backend Integration**: Comunicación con agentes de PipeWise

### Integración con Backend
Las herramientas se conectan automáticamente con los endpoints del backend:

```typescript
// Análisis de leads
POST /api/leads/analyze
{ "lead_data": "información del lead" }

// Programación de reuniones  
POST /api/calendar/schedule
{ "lead_email": "email", "meeting_type": "tipo" }

// Envío de emails
POST /api/integrations/email/send
{ "recipient": "email", "subject": "asunto", "content": "contenido" }

// Twitter DMs
POST /api/integrations/twitter/dm
{ "username": "usuario", "message": "mensaje" }
```

## Personalización

### Temas y Estilos
El sistema respeta el tema global de la aplicación:
- **Light Mode**: Colores claros con alta legibilidad
- **Dark Mode**: Tema oscuro automático
- **Animations**: Suaves y optimizadas para accesibilidad

### Agregar Nuevas Herramientas
1. Agregar la definición en `frontend/app/api/chat/route.ts`:

```typescript
const tools = {
  nueva_herramienta: {
    description: "Descripción de la nueva herramienta",
    parameters: {
      type: "object",
      properties: {
        parametro: {
          type: "string", 
          description: "Descripción del parámetro"
        }
      },
      required: ["parametro"]
    }
  }
};
```

2. Implementar el handler en la función `handleToolCall`
3. Agregar el endpoint correspondiente en el backend

### Configuración de Agentes
Los prompts del sistema se pueden ajustar modificando el `systemMessage` en el API route:

```typescript
const systemMessage = {
  role: "system" as const,
  content: `Personaliza aquí el comportamiento del asistente...`
};
```

## Troubleshooting

### Errores Comunes

#### 1. "OpenAI API key not configured"
- Verificar que `OPENAI_API_KEY` esté en `.env.local`
- Reiniciar el servidor de desarrollo

#### 2. "Failed to process chat message"
- Verificar conexión a internet
- Revisar logs del servidor para más detalles
- Verificar que el backend esté ejecutándose

#### 3. Herramientas no funcionan
- Verificar que `PIPEWISE_BACKEND_URL` esté configurado
- Confirmar que los endpoints del backend estén disponibles
- Revisar logs de la consola del navegador

### Debug Mode
Para habilitar logs detallados, agregar:

```env
NODE_ENV=development
```

## Roadmap Futuro

### Funcionalidades Planificadas
- [ ] **Grabación de Voz**: Integración con Web Speech API
- [ ] **Archivos Adjuntos**: Soporte para documentos y archivos
- [ ] **Historial Persistente**: Guardar conversaciones en Supabase
- [ ] **Múltiples Agentes**: Visualización de handoffs entre agentes
- [ ] **Comandos Personalizados**: Shortcuts para acciones frecuentes
- [ ] **Integración con CRM**: Sincronización bidireccional con sistemas externos

### Mejoras Técnicas
- [ ] **Rate Limiting**: Protección contra uso excesivo
- [ ] **Caching**: Cache inteligente de respuestas
- [ ] **Offline Support**: Funcionalidad básica sin conexión
- [ ] **PWA**: Progressive Web App capabilities

## Contribución

Para contribuir al sistema de chat:

1. **Fork** el repositorio
2. **Crear** una rama para tu feature
3. **Implementar** siguiendo las convenciones establecidas
4. **Probar** exhaustivamente
5. **Crear** pull request con descripción detallada

### Convenciones de Código
- **TypeScript**: Tipado estricto obligatorio
- **Components**: Usar forwardRef para componentes de UI
- **Hooks**: Custom hooks para lógica compartida
- **Styling**: Tailwind CSS con clases consistentes
- **Testing**: Tests unitarios para componentes críticos

---

## Soporte

Para soporte técnico o preguntas sobre implementación:
- 📧 Email: soporte@pipewise.com
- 💬 Chat: Usa el propio sistema de chat en `/chat`
- 📖 Docs: Consulta la documentación en `/docs`

**Versión**: 1.0.0  
**Última actualización**: Enero 2025  
**Compatibilidad**: Next.js 15+, React 19+, Node.js 18+ 