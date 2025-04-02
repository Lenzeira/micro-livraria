from concurrent import futures
import grpc
from grpc import StatusCode
import inventory_pb2
import inventory_pb2_grpc
from typing import List, Dict, Any

# Banco de dados em memória com tipo de dados definido
products_db: List[Dict[str, Any]] = [
    {"id": 1, "name": "Engenharia de Software Moderna", "quantity": 10, 
     "price": 99.90, "photo": "livro1.jpg", "author": "Marco Tulio Valente"},
    {"id": 2, "name": "Clean Code", "quantity": 5, 
     "price": 89.90, "photo": "livro2.jpg", "author": "Robert C. Martin"}
]

class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    def SearchAllProducts(self, request, context):
        """Lista todos os produtos com paginação"""
        try:
            response = inventory_pb2.ProductsResponse()
            for product in products_db:
                product_response = response.products.add()
                product_response.id = product["id"]
                product_response.name = product["name"]
                product_response.quantity = product["quantity"]
                product_response.price = product["price"]
                product_response.photo = product["photo"]
                product_response.author = product["author"]
            return response
        except Exception as e:
            context.set_code(StatusCode.INTERNAL)
            context.set_details(f"Erro interno: {str(e)}")
            return inventory_pb2.ProductsResponse()

    def SearchProductByID(self, request, context):
        """Busca um produto pelo ID com tratamento de erros"""
        try:
            product = next((p for p in products_db if p["id"] == request.id), None)
            if product:
                return inventory_pb2.ProductResponse(**product)
            context.set_code(StatusCode.NOT_FOUND)
            context.set_details("Produto não encontrado")
            return inventory_pb2.ProductResponse()
        except Exception as e:
            context.set_code(StatusCode.INTERNAL)
            context.set_details(f"Erro interno: {str(e)}")
            return inventory_pb2.ProductResponse()

    def AddProduct(self, request, context):
        """Adiciona produto com validação"""
        try:
            if not request.name or request.quantity < 0 or request.price <= 0:
                context.set_code(StatusCode.INVALID_ARGUMENT)
                context.set_details("Dados inválidos")
                return inventory_pb2.ProductResponse()

            new_id = max(p["id"] for p in products_db) + 1 if products_db else 1
            new_product = {
                "id": new_id,
                "name": request.name,
                "quantity": request.quantity,
                "price": request.price,
                "photo": request.photo or "",
                "author": request.author or ""
            }
            products_db.append(new_product)
            return inventory_pb2.ProductResponse(**new_product)
        except Exception as e:
            context.set_code(StatusCode.INTERNAL)
            context.set_details(f"Erro ao adicionar produto: {str(e)}")
            return inventory_pb2.ProductResponse()

    def UpdateProduct(self, request, context):
        """Atualiza produto com validação"""
        try:
            if not request.name or request.quantity < 0 or request.price <= 0:
                context.set_code(StatusCode.INVALID_ARGUMENT)
                context.set_details("Dados inválidos")
                return inventory_pb2.ProductResponse()

            for i, p in enumerate(products_db):
                if p["id"] == request.id:
                    products_db[i] = {
                        "id": request.id,
                        "name": request.name,
                        "quantity": request.quantity,
                        "price": request.price,
                        "photo": request.photo or p["photo"],
                        "author": request.author or p["author"]
                    }
                    return inventory_pb2.ProductResponse(**products_db[i])
            
            context.set_code(StatusCode.NOT_FOUND)
            context.set_details("Produto não encontrado")
            return inventory_pb2.ProductResponse()
        except Exception as e:
            context.set_code(StatusCode.INTERNAL)
            context.set_details(f"Erro ao atualizar produto: {str(e)}")
            return inventory_pb2.ProductResponse()

    def DeleteProduct(self, request, context):
        """Remove um produto pelo ID"""
        try:
            global products_db
            initial_count = len(products_db)
            products_db = [p for p in products_db if p["id"] != request.id]
            
            if len(products_db) == initial_count:
                context.set_code(StatusCode.NOT_FOUND)
                context.set_details("Produto não encontrado")
                return inventory_pb2.Empty()
            
            return inventory_pb2.Empty()
        except Exception as e:
            context.set_code(StatusCode.INTERNAL)
            context.set_details(f"Erro ao remover produto: {str(e)}")
            return inventory_pb2.Empty()

def serve():
    """Configuração aprimorada do servidor"""
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024)
        ]
    )
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryService(), server)
    server.add_insecure_port('[::]:50051')
    print("Servidor Inventory rodando na porta 50051...")
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Desligando servidor...")
        server.stop(0)

if __name__ == '__main__':
    serve()