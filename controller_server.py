from flask import Flask, jsonify, request
import grpc
import inventory_pb2
import inventory_pb2_grpc
import logging
from functools import wraps

# Configuração inicial
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração gRPC com timeout
GRPC_CHANNEL_OPTIONS = [
    ('grpc.connect_timeout_ms', 5000),
    ('grpc.keepalive_timeout_ms', 10000)
]
channel = grpc.insecure_channel('localhost:50051', options=GRPC_CHANNEL_OPTIONS)
stub = inventory_pb2_grpc.InventoryServiceStub(channel)

# Decorator para tratamento centralizado de erros
def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except grpc.RpcError as e:
            status_code = 500
            if e.code() == grpc.StatusCode.NOT_FOUND:
                status_code = 404
            elif e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                status_code = 400
            
            logger.error(f"Erro gRPC: {e.code().name} - {e.details()}")
            return jsonify({
                "status": "error",
                "message": e.details(),
                "code": e.code().name
            }), status_code
        except Exception as e:
            logger.error(f"Erro interno: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "Erro interno no servidor"
            }), 500
    return wrapper

# Middleware para log de requisições
@app.before_request
def log_request_info():
    logger.info(f"Requisição recebida: {request.method} {request.path}")

# Helper para respostas padrão
def create_response(data=None, message="", status="success", status_code=200):
    return jsonify({
        "status": status,
        "message": message,
        "data": data
    }), status_code

# Rotas CRUD
@app.route('/product/<int:id>', methods=['GET'])
@handle_errors
def get_product(id):
    response = stub.SearchProductByID(inventory_pb2.Payload(id=id))
    if not response.id:
        return create_response(
            message="Produto não encontrado",
            status="error",
            status_code=404
        )
    return create_response({
        "id": response.id,
        "name": response.name,
        "quantity": response.quantity,
        "price": response.price,
        "photo": response.photo,
        "author": response.author
    })

@app.route('/products', methods=['GET'])
@handle_errors
def get_all_products():
    response = stub.SearchAllProducts(inventory_pb2.Empty())
    products = [{
        "id": p.id,
        "name": p.name,
        "quantity": p.quantity,
        "price": p.price,
        "photo": p.photo,
        "author": p.author
    } for p in response.products]
    return create_response(products)

@app.route('/product', methods=['POST'])
@handle_errors
def add_product():
    data = request.get_json() or {}
    required_fields = ['name', 'quantity', 'price']
    if not all(field in data for field in required_fields):
        return create_response(
            message=f"Campos obrigatórios faltando: {required_fields}",
            status="error",
            status_code=400
        )

    response = stub.AddProduct(inventory_pb2.ProductRequest(
        id=0,  # ID será gerado pelo servidor
        name=data['name'],
        quantity=data['quantity'],
        price=data['price'],
        photo=data.get('photo', ''),
        author=data.get('author', '')
    ))
    return create_response(
        {"id": response.id},
        message="Produto adicionado com sucesso",
        status_code=201
    )

@app.route('/product/<int:id>', methods=['PUT'])
@handle_errors
def update_product(id):
    data = request.get_json() or {}
    response = stub.UpdateProduct(inventory_pb2.ProductRequest(
        id=id,
        name=data.get('name', ''),
        quantity=data.get('quantity', 0),
        price=data.get('price', 0.0),
        photo=data.get('photo', ''),
        author=data.get('author', '')
    ))
    return create_response(message="Produto atualizado com sucesso")

@app.route('/product/<int:id>', methods=['DELETE'])
@handle_errors
def delete_product(id):
    stub.DeleteProduct(inventory_pb2.Payload(id=id))
    return create_response(message="Produto removido com sucesso")

# Rota de health check
@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Testa a conexão com o servidor gRPC
        stub.SearchProductByID(inventory_pb2.Payload(id=0))
        return jsonify({"status": "healthy"}), 200
    except grpc.RpcError:
        return jsonify({"status": "unhealthy"}), 503

if __name__ == '__main__':
    logger.info("Iniciando servidor Controller na porta 3000...")
    app.run(host='0.0.0.0', port=3000, debug=False)