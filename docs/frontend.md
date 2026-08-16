# Frontend: Web Client

## Overview

The [frontend](../frontend) repository focuses on the browser implementation of the web client. It is built with React and Vite, written in TypeScript. 

The directory structure is as follows:
```text
frontend/
├-─ public/          
├── src/
│   ├── assets/      Images and other imported assets
│   ├── components/  Reusable UI components
│   ├── contexts/    React context definitions
│   ├── hooks/       Reusable React hooks
│   ├── pages/       Application pages
│   ├── protocols/   Signaling protocol definitions
│   ├── providers/   Context providers and application state
│   ├── services/    Low-level browser API implementation
│   ├── types/       Shared models
│   ├── App.tsx      Application routes and provider setup
│   └── main.tsx     Application entry point
├── index.html       
├── package.json    
└── vite.config.ts   
```

Contexts, providers, and hooks are separated into their own directories. Providers manage application state and use the lower-level functionality exposed by `services/`.

