#!/usr/bin/env python3
"""
Sistema de Telemetria E-Racing UNICAMP - Run Dinamômetro
Script simplificado para executar telemetria de dinamômetro
"""

import sys
import os

def check_dependencies():
    """Verifica dependências."""
    required_packages = ['PIL', 'matplotlib', 'watchdog']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                __import__('PIL')
            else:
                __import__(package.lower())
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Dependências não encontradas:")
        for pkg in missing_packages:
            print(f"   • {pkg}")
        print("\n💡 Execute o comando abaixo para instalar:")
        
        # Converte PIL para Pillow
        install_list = [pkg if pkg != 'PIL' else 'Pillow' for pkg in missing_packages]
        print(f"   pip install {' '.join(install_list)}")
        return False
    
    return True

def check_display():
    """Verifica se há display disponível para interface gráfica."""
    import os
    return os.environ.get('DISPLAY') is not None

def run_telemetry():
    """Executa sistema de telemetria."""
    print("🚀 Iniciando Sistema de Telemetria Dinamômetro E-Racing UNICAMP...")
    
    # Verifica dependências
    if not check_dependencies():
        sys.exit(1)
    
    # Verifica display disponível
    if not check_display():
        print("\n⚠️ AVISO: Nenhum display gráfico detectado!")
        print("💡 Para executar em ambiente headless:")
        print("   xvfb-run python run_dyno.py")
        print("   ou")
        print("   export DISPLAY=:0 && python run_dyno.py")
        print("\n🎯 Alternativa: Execute com dados de teste para verificação")
        
        # Continua mesmo sem display para testar lógica
        response = input("\nContinuar mesmo assim? (s/n): ").lower().strip()
        if response != 's':
            print("❌ Execução cancelada.")
            return
    
    try:
        # Importa e executa
        from main_dyno import main
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Sistema interrompido pelo usuário.")
    except Exception as e:
        print(f"❌ Erro ao executar sistema: {e}")
        print("\n💡 Soluções possíveis:")
        print("   1. Instalar Xvfb: apt-get install xvfb")
        print("   2. Executar com: xvfb-run python run_dyno.py")
        print("   3. Configurar DISPLAY: export DISPLAY=:0")
        import traceback
        traceback.print_exc()

def main():
    """Função principal."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              🏎️  E - R A C I N G   U N I C A M P  ⚡          ║
║                                                               ║
║              SISTEMA DE TELEMETRIA - DINAMÔMETRO              ║
║                                                               ║
║      Script de execução simplificado do dashboard dyno        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Argumentos de linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("""
Uso: python run_dyno.py [opção]

Opções:
  --help, -h     Mostra esta ajuda
  --check        Verifica dependências apenas
  --version      Mostra versão
  (sem args)     Executa o sistema

Exemplos:
  python run_dyno.py                    # Executa sistema completo
  python run_dyno.py --check            # Verifica dependências
  python run_dyno.py --help             # Mostra ajuda
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
Versão: 2.0 Dinamômetro
Desenvolvido para testes em dinamômetro - Formula SAE Electric 2025
Foco: VCU, Motores e Inversores
            """)
            return
    
    # Executa sistema
    run_telemetry()

if __name__ == '__main__':
    main()