import os
from flask import Flask, render_template, request, redirect, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF  # Usamos fpdf2 en lugar de WeasyPrint

# --- 1. CONFIGURACIÓN DE LA APLICACIÓN ---
app = Flask(__name__)

# Configuración de la base de datos para funcionar en Railway y localmente
db_url = os.environ.get("DATABASE_URL")
if db_url:
    db_url = db_url.replace("postgres://", "postgresql://", 1)
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_url = "sqlite:///" + os.path.join(basedir, "productos.db")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# --- 2. MODELO DE LA BASE DE DATOS ---
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    precio_sugerido = db.Column(db.Float, nullable=True)
    estatus = db.Column(db.String(20), default="stock")
    nota = db.Column(db.Text, nullable=True)
    cantidad_total = db.Column(db.Integer, default=1)
    cantidad_pagada = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Producto {self.nombre}>"


# --- 3. RUTAS DE LA APLICACIÓN ---
@app.route("/")
def index():
    # Crea las tablas de la base de datos si no existen
    with app.app_context():
        db.create_all()

    # Lógica de paginación
    page = request.args.get("page", 1, type=int)
    paginacion = Producto.query.paginate(page=page, per_page=20)

    return render_template("index.html", paginacion=paginacion)


@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nuevo_producto = Producto(
            nombre=request.form["nombre"],
            precio=float(request.form["precio"]),
            precio_sugerido=(
                float(request.form["precio_sugerido"])
                if request.form["precio_sugerido"]
                else 0.0
            ),
            estatus=request.form["estatus"],
            nota=request.form["nota"],
            cantidad_total=int(request.form["cantidad_total"]),
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("agregar.html")


@app.route("/modificar_pagado/<int:producto_id>/<string:accion>", methods=["POST"])
def modificar_pagado(producto_id, accion):
    """Incrementa o decrementa la cantidad pagada de un producto."""
    producto = db.get_or_404(Producto, producto_id)
    if accion == "incrementar" and producto.cantidad_pagada < producto.cantidad_total:
        producto.cantidad_pagada += 1
    elif accion == "decrementar" and producto.cantidad_pagada > 0:
        producto.cantidad_pagada -= 1
    db.session.commit()
    return render_template("_producto_fila.html", producto=producto)


@app.route("/aumentar_stock/<int:producto_id>", methods=["POST"])
def aumentar_stock(producto_id):
    """Aumenta la cantidad total (stock) de un producto."""
    producto = db.get_or_404(Producto, producto_id)
    producto.cantidad_total += 1
    db.session.commit()
    return render_template("_producto_fila.html", producto=producto)


# --- RUTA DE REPORTE CON FPDF2 ---
@app.route("/reporte/pdf")
def generar_reporte_pdf():
    productos = Producto.query.all()

    total_pendiente = sum(
        p.precio * (p.cantidad_total - p.cantidad_pagada) for p in productos
    )
    total_stock = sum(
        p.precio * p.cantidad_total for p in productos if p.estatus == "stock"
    )

    # Clase para definir el formato del PDF con cabecera y pie de página
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", "B", 15)
            self.cell(0, 10, "Reporte de Inventario Pro", 0, 1, "C")
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "I", 8)
            self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

    # Creación del objeto PDF
    pdf = PDF()
    pdf.add_page()

    # Título y contenido del reporte
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, "Resumen Financiero:", 0, 1)
    pdf.ln(5)

    pendiente_str = f"${total_pendiente:,.2f}"
    stock_str = f"${total_stock:,.2f}"

    pdf.cell(50, 10, "Total Pendiente de Pago:", 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, pendiente_str, 0, 1)

    pdf.set_font("Arial", "", 12)
    pdf.cell(50, 10, "Valor Total en Stock:", 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, stock_str, 0, 1)

    # Generación y envío del archivo PDF
    pdf_output = pdf.output(dest="S").encode("latin-1")

    return Response(
        pdf_output,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment;filename=reporte_inventario.pdf"},
    )


# --- INICIO DE LA APLICACIÓN (PARA DESARROLLO LOCAL) ---
if __name__ == "__main__":
    app.run(debug=True)
