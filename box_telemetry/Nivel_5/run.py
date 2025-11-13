#!/usr/bin/env python3
"""
Script de Execução - Sistema de Telemetria E-Racing UNICAMP
Script simplificado para executar o sistema de telemetria
"""

import sys
import os
import subprocess

def check_dependencies():
    """Verifica se as dependências estão instaladas."""
    required_packages = ['PIL', 'matplotlib', 'watchdog']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.lower().replace('pil', 'PIL'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Dependências não encontradas:")
        for pkg in missing_packages:
            print(f"   • {pkg}")
        print("\n💡 Execute o comando abaixo para instalar:")
        print(f"   pip install {' '.join(missing_packages)}")
        print("\n📁 Ou use o arquivo requirements.txt:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def run_telemetry():
    """Executa o sistema de telemetria."""
    print("🚀 Iniciando Sistema de Telimetria E-Racing UNICAMP...")
    
    # Verifica dependências
    if not check_dependencies():
        sys.exit(1)
    
    try:
        # Importa e executa aplicação principal
        from main import main
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Sistema interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro ao executar sistema: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Função principal do script."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║              🏎️  E - R A C I N G   U N I C A M P  ⚡              ║
║                                                                   ║
║                  SISTEMA DE TELEMETRIA                            ║
║                                                                   ║
║        Script de execução simplificado do dashboard              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Argumentos de linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
Uso: python run.py [opção]

Opções:
  --help, -h     Mostra esta ajuda
  --check        Verifica dependências apenas
  --version      Mostra versão
  (sem args)     Executa o sistema

Exemplos:
  python run.py                    # Executa sistema completo
  python run.py --check            # Verifica dependências
  python run.py --help             # Mostra ajuda
            """)
            return
        elif sys.argv[1] == '--check':
            print("🔍 Verificando dependências...")
            if check_dependencies():
                print("✅ Todas as dependências estão instaladas!")
            return
        elif sys.argv[1] == '--version':
            print("""
Sistema de Telemetria E-Racing UNICAMP
Versão: 2.0 Modular
Desenvolvido para Formula SAE Electric 2025
            """)
            return
    
    # Executa sistema
    run_telemetry()

if __name__ == '__main__':
    main()
