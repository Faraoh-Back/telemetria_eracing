#!/usr/bin/env python3
"""
Teste das correções - verificar se não abre janelas duplicadas
"""

import sys
import os

def test_ui_singleton():
    """Testa se UI manager cria apenas uma janela"""
    print("🧪 TESTANDO PROTEÇÃO CONTRA JANELAS DUPLICADAS")
    print("="*60)
    
    try:
        # Importar módulos
        from data_manager_dyno import DynoDataManager
        from ui_manager_dyno import DynoTelemetryUI
        
        print("✅ Imports OK")
        
        # Criar componentes
        data_manager = DynoDataManager()
        ui_manager = DynoTelemetryUI(data_manager)
        
        print("✅ Data Manager e UI Manager criados")
        
        # Primeira criação
        print("\n🔧 Criando primeira janela...")
        root1 = ui_manager.create_main_window()
        print(f"✅ Primeira janela criada: {root1}")
        
        # Segunda criação (deve retornar a mesma)
        print("\n🔧 Tentando criar segunda janela...")
        root2 = ui_manager.create_main_window()
        print(f"✅ Segunda janela: {root2}")
        
        # Verificar se são a mesma
        if root1 == root2:
            print("\n✅ SUCESSO: É a mesma janela!")
            print("🎯 Proteção contra duplicação funcionando!")
            
            # Fechar janela
            print("\n🛑 Fechando janela...")
            ui_manager.on_closing()
            
            return True
        else:
            print("\n❌ ERRO: Janelas diferentes!")
            print(f"Root1: {root1}")
            print(f"Root2: {root2}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Testa imports básicos"""
    print("🔍 TESTANDO IMPORTS")
    print("="*30)
    
    try:
        import config_dyno
        print("✅ config_dyno")
        
        from data_manager_dyno import DynoDataManager
        print("✅ data_manager_dyno")
        
        from ui_manager_dyno import DynoTelemetryUI
        print("✅ ui_manager_dyno")
        
        from smart_log_monitor_simple import create_smart_log_monitor
        print("✅ smart_log_monitor_simple")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        return False

if __name__ == "__main__":
    print("🧪 INICIANDO TESTES DAS CORREÇÕES")
    print("="*60)
    
    # Teste 1: Imports
    if not test_imports():
        print("\n❌ Falha nos imports")
        sys.exit(1)
    
    # Teste 2: UI Singleton
    if not test_ui_singleton():
        print("\n❌ Falha no teste de UI singleton")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("🎉 Correções funcionando corretamente!")
    print("="*60)
    print("\n🚀 Você pode agora executar:")
    print("   xvfb-run python3 run_dyno.py")
    print("   (e deve ver apenas uma janela)")
    
    sys.exit(0)