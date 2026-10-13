# Configuraciones de shell (previsualización)

Esta carpeta contiene las configuraciones de shell que el script usa para la
**previsualización** y para aplicar la opción elegida en el menú de selección.

| Archivo | Descripción |
| --- | --- |
| `zshrc.powerlevel10k` | `.zshrc` que se aplica al elegir la opción **Powerlevel10k**. |
| `zshrc.oh-my-zsh` | `.zshrc` que se aplica al elegir la opción **Oh My Zsh only**. |
| `p10k.zsh` | Configuración de Powerlevel10k que se copia a `~/.p10k.zsh`. |

## Notas

- Estas configuraciones provienen del entorno real del autor del proyecto.
- Las rutas absolutas del usuario original (por ejemplo `/home/alex`) ya están
  normalizadas a `$HOME`, y al aplicarlas el script vuelve a normalizarlas.
- Antes de sobrescribir, tu `~/.zshrc` se respalda como
  `~/.zshrc.post_install.<fecha>.bak`.
- Puedes editar estos archivos para personalizar lo que se instala.
