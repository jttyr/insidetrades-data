# InsideTrades – datos en la nube + EA en VPS
1. Repo publico `insidetrades-data` con esta carpeta (workflow `insidetrades-data.yml` genera data/*.csv dos veces al dia).
2. EA `NasdaqSMC_EA_v10`: InpDataURL = https://raw.githubusercontent.com/<USUARIO>/insidetrades-data/main/data/
3. MT5 > Herramientas > Opciones > Asesores Expertos > "Permitir WebRequest" y agregar https://raw.githubusercontent.com
4. MT5 > Herramientas > Opciones > Notificaciones: tu MetaQuotes ID (App MT5 del celular > Ajustes > Mensajes).
5. VPS (boton "VPS" abajo a la derecha de MT5 de escritorio): migrar experto + ajustes. Queda corriendo sin tu computadora.
