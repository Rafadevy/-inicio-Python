#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface para gerenciar o banco de conhecimento."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime


class KnowledgeManager:
    """Gerenciador do banco de conhecimento."""
    
    def __init__(self, parent, knowledge_base):
        self.parent = parent
        self.kb = knowledge_base
        self.current_tab = None
        
    def create_knowledge_tab(self, notebook):
        """Criar aba de gerenciamento de conhecimento."""
        self.current_tab = ttk.Frame(notebook)
        notebook.add(self.current_tab, text="📚 Meu Conhecimento")
        
        # Frame de controle
        control_frame = ttk.LabelFrame(self.current_tab, text="Adicionar Fontes", padding="10")
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Botões de ação
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="📝 Adicionar Texto", 
                  command=self.add_text_source).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📄 Adicionar PDF", 
                  command=self.add_pdf_source).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🖼️ Adicionar Imagem", 
                  command=self.add_image_source).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔍 Pesquisar", 
                  command=self.search_knowledge).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📊 Estatísticas", 
                  command=self.show_statistics).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🗑️ Limpar Tudo", 
                  command=self.clear_all).pack(side="left", padx=5)
        
        # Lista de fontes
        sources_frame = ttk.LabelFrame(self.current_tab, text="Minhas Fontes", padding="10")
        sources_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Treeview para listar fontes
        columns = ("ID", "Título", "Tipo", "Data", "Fórmulas", "Números")
        self.sources_tree = ttk.Treeview(sources_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.sources_tree.heading(col, text=col)
            if col == "Título":
                self.sources_tree.column(col, width=300)
            elif col == "ID":
                self.sources_tree.column(col, width=80)
            else:
                self.sources_tree.column(col, width=100)
        
        scrollbar_y = ttk.Scrollbar(sources_frame, orient="vertical", command=self.sources_tree.yview)
        scrollbar_x = ttk.Scrollbar(sources_frame, orient="horizontal", command=self.sources_tree.xview)
        self.sources_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.sources_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        sources_frame.grid_rowconfigure(0, weight=1)
        sources_frame.grid_columnconfigure(0, weight=1)
        
        # Bind de duplo clique para ver conteúdo
        self.sources_tree.bind("<Double-1>", self.view_source)
        self.sources_tree.bind("<Delete>", self.delete_source)
        
        # Botão de deletar
        btn_delete = ttk.Button(sources_frame, text="Deletar Selecionado (Del)", 
                                command=self.delete_selected)
        btn_delete.grid(row=2, column=0, pady=5)
        
        # Área de consulta
        query_frame = ttk.LabelFrame(self.current_tab, text="Consultar Conhecimento", padding="10")
        query_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(query_frame, text="Faça uma pergunta em linguagem natural:").pack(anchor="w")
        
        text_frame = ttk.Frame(query_frame)
        text_frame.pack(fill="x", pady=5)
        
        self.query_text = tk.Text(text_frame, height=3, width=80)
        self.query_text.pack(side="left", fill="x", expand=True)
        
        btn_query = ttk.Button(text_frame, text="💬 Perguntar", command=self.ask_question)
        btn_query.pack(side="right", padx=5)
        
        # Área de resposta
        response_frame = ttk.LabelFrame(self.current_tab, text="Resposta", padding="10")
        response_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.response_text = scrolledtext.ScrolledText(
            response_frame, height=12, wrap=tk.WORD, font=("Consolas", 10)
        )
        self.response_text.pack(fill="both", expand=True)
        
        # Atualizar lista
        self.refresh_sources_list()
        
        return self.current_tab
    
    def add_text_source(self):
        """Adicionar fonte de texto manualmente."""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Adicionar Texto")
        dialog.geometry("600x500")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Título:", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        title_entry = ttk.Entry(dialog, width=60)
        title_entry.pack(padx=10, fill="x")
        
        ttk.Label(dialog, text="Conteúdo:", font=("", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        text_area = scrolledtext.ScrolledText(dialog, height=15)
        text_area.pack(padx=10, fill="both", expand=True)
        
        def save():
            title = title_entry.get().strip()
            content = text_area.get("1.0", "end-1c").strip()
            
            if title and content:
                source = self.kb.add_source(title, content, "text")
                messagebox.showinfo("Sucesso", f"Fonte '{title}' adicionada!\n\n"
                                   f"Fórmulas encontradas: {len(source.formulas)}\n"
                                   f"Números encontrados: {len(source.numbers)}")
                dialog.destroy()
                self.refresh_sources_list()
            else:
                messagebox.showwarning("Aviso", "Preencha título e conteúdo!")
        
        ttk.Button(dialog, text="Salvar", command=save).pack(pady=10)
    
    def add_pdf_source(self):
        """Adicionar fonte de PDF."""
        file_path = filedialog.askopenfilename(
            title="Selecionar PDF",
            filetypes=[("PDF files", "*.pdf"), ("Todos", "*.*")]
        )
        
        if file_path:
            # Extrair texto do PDF
            try:
                from deepseek_calc import extract_text_from_pdf
                content = extract_text_from_pdf(file_path)
                title = Path(file_path).stem
                source = self.kb.add_source(title, content, "pdf", file_path)
                messagebox.showinfo("Sucesso", f"PDF '{title}' adicionado!\n\n"
                                   f"Fórmulas encontradas: {len(source.formulas)}\n"
                                   f"Números encontrados: {len(source.numbers)}")
                self.refresh_sources_list()
            except ImportError:
                messagebox.showerror("Erro", "Dependências não instaladas. Execute: pip install pypdf pdf2image")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao processar PDF: {e}")
    
    def add_image_source(self):
        """Adicionar fonte de imagem (OCR)."""
        file_path = filedialog.askopenfilename(
            title="Selecionar Imagem",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("Todos", "*.*")]
        )
        
        if file_path:
            try:
                from deepseek_calc import ocr_text_from_image
                content = ocr_text_from_image(file_path)
                title = Path(file_path).stem
                source = self.kb.add_source(title, content, "image", file_path)
                messagebox.showinfo("Sucesso", f"Imagem '{title}' adicionada!\n\n"
                                   f"Fórmulas encontradas: {len(source.formulas)}\n"
                                   f"Números encontrados: {len(source.numbers)}")
                self.refresh_sources_list()
            except ImportError:
                messagebox.showerror("Erro", "Dependências não instaladas. Execute: pip install pillow pytesseract")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao processar imagem: {e}")
    
    def search_knowledge(self):
        """Buscar no conhecimento."""
        query = tk.simpledialog.askstring("Buscar", "Digite sua busca:", parent=self.parent)
        if query:
            results = self.kb.search(query)
            
            if results:
                result_text = f"🔍 Resultados para: '{query}'\n"
                result_text += "=" * 60 + "\n\n"
                
                for source, score in results[:5]:
                    result_text += f"📄 {source.title}\n"
                    result_text += f"   Relevância: {score:.2%}\n"
                    result_text += f"   Tipo: {source.source_type}\n"
                    result_text += f"   Fórmulas: {len(source.formulas)} | Números: {len(source.numbers)}\n"
                    result_text += f"   Prévia: {source.content[:200]}...\n\n"
                
                self.response_text.delete("1.0", "end")
                self.response_text.insert("1.0", result_text)
            else:
                messagebox.showinfo("Sem resultados", "Nenhuma fonte encontrada para esta busca.")
    
    def ask_question(self):
        """Fazer pergunta baseada no conhecimento."""
        query = self.query_text.get("1.0", "end-1c").strip()
        if not query:
            messagebox.showwarning("Aviso", "Digite uma pergunta!")
            return
        
        # Consultar conhecimento
        context = self.kb.query_knowledge(query)
        
        # Construir resposta
        response = f"💡 PERGUNTA: {query}\n"
        response += "=" * 60 + "\n\n"
        
        if context.extracted_formulas:
            response += "📐 FÓRMULAS ENCONTRADAS:\n"
            for formula in context.extracted_formulas[:5]:
                expr = formula.get('expression', formula.get('source_text', str(formula)))
                response += f"   • {expr}\n"
            response += "\n"
        
        if context.extracted_numbers:
            response += "🔢 NÚMEROS RELEVANTES:\n"
            unique_numbers = list(set(context.extracted_numbers))[:10]
            response += f"   {', '.join(str(n) for n in unique_numbers)}\n\n"
        
        if context.relevant_sources:
            response += "📚 FONTES CONSULTADAS:\n"
            for source in context.relevant_sources[:3]:
                response += f"   • {source.title} ({source.source_type})\n"
            response += "\n"
        
        if not context.extracted_formulas and not context.extracted_numbers:
            response += "ℹ️ Nenhuma informação específica encontrada no conhecimento.\n"
            response += "   Tente adicionar mais fontes ou reformular a pergunta.\n"
        
        # Tentar calcular se for uma expressão matemática
        try:
            from deepseek_calc import calculate_expression
            result, msg = calculate_expression(query)
            if result is not None:
                response += "\n" + "=" * 60 + "\n"
                response += f"🧮 RESULTADO DO CÁLCULO: {result}\n"
                if msg and msg != str(result):
                    response += f"   ({msg})\n"
        except Exception:
            pass
        
        self.response_text.delete("1.0", "end")
        self.response_text.insert("1.0", response)
    
    def refresh_sources_list(self):
        """Atualizar lista de fontes."""
        # Limpar lista
        for item in self.sources_tree.get_children():
            self.sources_tree.delete(item)
        
        # Adicionar fontes
        for source in self.kb.sources.values():
            self.sources_tree.insert("", "end", values=(
                source.id[:8],
                source.title[:50],
                source.source_type,
                source.uploaded_at[:10],
                len(source.formulas),
                len(source.numbers)
            ), tags=(source.id,))
    
    def view_source(self, event):
        """Ver conteúdo de uma fonte."""
        selection = self.sources_tree.selection()
        if selection:
            item = selection[0]
            tags = self.sources_tree.item(item, "tags")
            if tags:
                source_id = tags[0]
                source = self.kb.sources.get(source_id)
                
                if source:
                    viewer = tk.Toplevel(self.parent)
                    viewer.title(f"Conteúdo: {source.title}")
                    viewer.geometry("800x600")
                    viewer.transient(self.parent)
                    
                    text_widget = scrolledtext.ScrolledText(viewer, wrap=tk.WORD, font=("Consolas", 10))
                    text_widget.pack(fill="both", expand=True, padx=10, pady=10)
                    
                    # Mostrar conteúdo
                    content = f"📄 TÍTULO: {source.title}\n"
                    content += f"🆔 ID: {source.id}\n"
                    content += f"📁 TIPO: {source.source_type}\n"
                    content += f"📅 DATA: {source.uploaded_at}\n"
                    content += f"📊 CARACTERES: {source.metadata['char_count']:,}\n"
                    content += f"📐 FÓRMULAS: {len(source.formulas)}\n"
                    content += f"🔢 NÚMEROS: {len(source.numbers)}\n"
                    content += "=" * 60 + "\n\n"
                    
                    if source.formulas:
                        content += "FÓRMULAS ENCONTRADAS:\n"
                        for f in source.formulas[:10]:
                            content += f"  • {f.get('expression', f)}\n"
                        content += "\n"
                    
                    if source.numbers:
                        content += "NÚMEROS ENCONTRADOS:\n"
                        content += f"  {', '.join(str(n) for n in source.numbers[:20])}\n\n"
                    
                    content += "CONTEÚDO COMPLETO:\n"
                    content += "-" * 60 + "\n"
                    content += source.content
                    
                    text_widget.insert("1.0", content)
                    text_widget.config(state="disabled")
    
    def delete_source(self, event=None):
        """Deletar fonte selecionada."""
        self.delete_selected()
    
    def delete_selected(self):
        """Deletar fonte selecionada."""
        selection = self.sources_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione uma fonte para deletar.")
            return
        
        if messagebox.askyesno("Confirmar", "Deseja realmente deletar esta fonte?"):
            for item in selection:
                tags = self.sources_tree.item(item, "tags")
                if tags:
                    source_id = tags[0]
                    if self.kb.delete_source(source_id):
                        self.sources_tree.delete(item)
            
            messagebox.showinfo("Sucesso", "Fonte(s) deletada(s) com sucesso!")
    
    def clear_all(self):
        """Limpar todo o conhecimento."""
        if messagebox.askyesno("Confirmar", 
                               "ATENÇÃO! Isso irá apagar TODAS as fontes de conhecimento.\n"
                               "Esta ação não pode ser desfeita.\n\n"
                               "Deseja continuar?"):
            for source_id in list(self.kb.sources.keys()):
                self.kb.delete_source(source_id)
            self.refresh_sources_list()
            messagebox.showinfo("Conhecimento Limpo", "Todas as fontes foram removidas.")
    
    def show_statistics(self):
        """Mostrar estatísticas do conhecimento."""
        stats = self.kb.get_statistics()
        
        stats_text = "📊 ESTATÍSTICAS DO CONHECIMENTO\n"
        stats_text += "=" * 40 + "\n\n"
        stats_text += f"📚 Total de fontes: {stats['total_sources']}\n"
        stats_text += f"📝 Total de caracteres: {stats['total_characters']:,}\n"
        stats_text += f"📐 Total de fórmulas: {stats['total_formulas']}\n"
        stats_text += f"🔢 Total de números: {stats['total_numbers']}\n\n"
        stats_text += "📁 Fontes por tipo:\n"
        for source_type, count in stats['source_types'].items():
            stats_text += f"   • {source_type}: {count}\n"
        
        messagebox.showinfo("Estatísticas do Conhecimento", stats_text)