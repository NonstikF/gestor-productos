import os
from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from weasyprint import HTML

app = Flask(__name__)
db_url = os.environ.get('DATABASE_URL')
if db_url:
    db_url = db_url.replace("postgres://", "postgresql://", 1)
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_url = 'sqlite:///' + os.path.join(basedir, 'productos.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- MODELO DE BASE DE DATOS ACTUALIZADO ---
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    precio_sugerido = db.Column(db.Float, nullable=True)
    estatus = db.Column(db.String(20), default='stock')
    nota = db.Column(db.Text, nullable=True)
    
    # --- CAMPOS MODIFICADOS ---
    # 'cantidad' ahora es 'cantidad_total'
    cantidad_total = db.Column(db.Integer, default=1)
    # Nuevo campo para rastrear cuántos están pagados
    cantidad_pagada = db.Column(db.Integer, default=0)
    # El campo 'pagado' (booleano) ya no es necesario y se elimina

    def __repr__(self):
        return f'<Producto {self.nombre}>'


# --- RUTAS DE LA APLICACIÓN ---
@app.route('/')
def index():
    with app.app_context():
        db.create_all()
    page = request.args.get('page', 1, type=int)
    paginacion = Producto.query.paginate(page=page, per_page=20)
    return render_template('index.html', paginacion=paginacion)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        # Al agregar, 'cantidad_pagada' siempre empieza en 0
        nuevo_producto = Producto(
            nombre=request.form['nombre'],
            precio=float(request.form['precio']),
            precio_sugerido=float(request.form['precio_sugerido']) if request.form['precio_sugerido'] else 0.0,
            estatus=request.form['estatus'],
            nota=request.form['nota'],
            cantidad_total=int(request.form['cantidad_total'])
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('agregar.html')

# --- NUEVAS RUTAS DE ACCIONES ---
@app.route('/modificar_pagado/<int:producto_id>/<string:accion>', methods=['POST'])
def modificar_pagado(producto_id, accion):
    """Incrementa o decrementa la cantidad pagada de un producto."""
    producto = db.get_or_404(Producto, producto_id)
    if accion == 'incrementar' and producto.cantidad_pagada < producto.cantidad_total:
        producto.cantidad_pagada += 1
    elif accion == 'decrementar' and producto.cantidad_pagada > 0:
        producto.cantidad_pagada -= 1
    db.session.commit()
    return render_template('_producto_fila.html', producto=producto)

@app.route('/aumentar_stock/<int:producto_id>', methods=['POST'])
def aumentar_stock(producto_id):
    """Aumenta la cantidad total (stock) de un producto."""
    producto = db.get_or_404(Producto, producto_id)
    producto.cantidad_total += 1
    db.session.commit()
    return render_template('_producto_fila.html', producto=producto)

# --- RUTA DE REPORTE ACTUALIZADA ---
@app.route('/reporte/pdf')
def generar_reporte_pdf():
    productos = Producto.query.all()
    # La lógica ahora calcula sobre los artículos no pagados
    total_pendiente = sum(p.precio * (p.cantidad_total - p.cantidad_pagada) for p in productos)
    total_stock = sum(p.precio * p.cantidad_total for p in productos if p.estatus == 'stock')
    
    html_renderizado = render_template('reporte.html', total_pendiente=total_pendiente, total_stock=total_stock)
    pdf = HTML(string=html_renderizado).write_pdf()
    return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition':'attachment;filename=reporte_inventario.pdf'})

if __name__ == '__main__':
    app.run(debug=True)