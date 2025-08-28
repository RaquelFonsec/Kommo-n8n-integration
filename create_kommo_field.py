#!/usr/bin/env python3
"""
Script para criar o campo personalizado 'bot_ativo' no Kommo CRM
Execute este script uma vez para configurar o campo necessário
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class KommoFieldCreator:
    def __init__(self):
        self.base_url = os.getenv('KOMMO_BASE_URL', 'https://previdas.kommo.com')
        self.api_url = f"{self.base_url}/api/v4"
        self.access_token = os.getenv('KOMMO_ACCESS_TOKEN')
        self.account_id = os.getenv('KOMMO_ACCOUNT_ID')
        
    async def get_headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    async def create_bot_ativo_field(self):
        """Cria o campo personalizado 'bot_ativo' no Kommo"""
        try:
            # Endpoint correto para campos personalizados
            url = f"{self.api_url}/leads/custom_fields"
            headers = await self.get_headers()
            
            # Payload para criar campo personalizado (corrigido)
            payload = {
                "name": "Bot Ativo",
                "type": "checkbox",
                "is_visible": True,
                "is_required": False,
                "is_deletable": True,
                "is_api_only": False,
                "request_id": "bot_ativo_field"
            }
            
            print("🔧 Criando campo 'bot_ativo' no Kommo...")
            print(f"📡 URL: {url}")
            print(f"📦 Payload: {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 201:
                        result = await response.json()
                        print("✅ Campo 'bot_ativo' criado com sucesso!")
                        print(f"📋 ID do campo: {result.get('id')}")
                        print(f"📋 Código do campo: {result.get('code')}")
                        return result
                    elif response.status == 409:
                        print("⚠️ Campo 'bot_ativo' já existe!")
                        return await self.get_existing_field()
                    else:
                        error_text = await response.text()
                        print(f"❌ Erro ao criar campo: {response.status}")
                        print(f"📄 Resposta: {error_text}")
                        return None
                        
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    async def get_existing_field(self):
        """Busca campo existente"""
        try:
            url = f"{self.api_url}/leads/custom_fields"
            headers = await self.get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        fields = result.get('_embedded', {}).get('custom_fields', [])
                        
                        for field in fields:
                            if field.get('code') == 'bot_ativo':
                                print(f"✅ Campo 'bot_ativo' encontrado!")
                                print(f"📋 ID: {field.get('id')}")
                                print(f"📋 Nome: {field.get('name')}")
                                return field
                        
                        print("❌ Campo 'bot_ativo' não encontrado na lista")
                        return None
                    else:
                        print(f"❌ Erro ao buscar campos: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Erro ao buscar campo: {e}")
            return None

async def main():
    print("🚀 Script para criar campo 'bot_ativo' no Kommo")
    print("=" * 50)
    
    # Verificar variáveis de ambiente
    required_vars = ['KOMMO_ACCESS_TOKEN', 'KOMMO_ACCOUNT_ID', 'KOMMO_BASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Variáveis de ambiente faltando:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Configure o arquivo .env com as credenciais do Kommo")
        return
    
    creator = KommoFieldCreator()
    result = await creator.create_bot_ativo_field()
    
    if result:
        print("\n🎉 Campo 'bot_ativo' configurado com sucesso!")
        print("📋 Agora você pode usar os comandos #pausar e #voltar no WhatsApp")
    else:
        print("\n❌ Falha ao configurar campo 'bot_ativo'")
        print("📞 Verifique as credenciais e tente novamente")

if __name__ == "__main__":
    asyncio.run(main())
