#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import hashlib
import pickle
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class KnowledgeSource:
    """Uma fonte de conhecimento (documento, texto, PDF)."""
    id: str
    title: str
    content: str
    source_type: str  # 'text', 'pdf', 'image'
    file_path: str
    uploaded_at: str
    metadata: Dict[str, Any]
    
    # Extracted information
    formulas: List[Dict[str, Any]]
    numbers: List[float]
    entities: Dict[str, List[str]]


@dataclass
class QueryContext:
    """Contexto de uma consulta do usuário."""
    query: str
    relevant_sources: List[KnowledgeSource]
    extracted_formulas: List[Dict[str, Any]]
    extracted_numbers: List[float]
    timestamp: str


class KnowledgeBase:
    """Banco de conhecimento personalizável."""
    
    def __init__(self, base_path: Path = None):
        if base_path is None:
            base_path = Path(__file__).parent / "knowledge"
        
        self.base_path = base_path
        self.sources_path = base_path / "sources"
        self.index_path = base_path / "index.json"
        self.embeddings_path = base_path / "embeddings.pkl"
        
        # Criar diretórios
        self.sources_path.mkdir(parents=True, exist_ok=True)
        
        # Carregar índice
        self.sources: Dict[str, KnowledgeSource] = {}
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self._embeddings_matrix = None
        
        self.load_index()
        
    def load_index(self):
        """Carregar índice do conhecimento."""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for source_data in data.get('sources', []):
                        source = KnowledgeSource(**source_data)
                        self.sources[source.id] = source
            except Exception as e:
                print(f"Erro ao carregar índice: {e}")
        
        if self.embeddings_path.exists():
            try:
                with open(self.embeddings_path, 'rb') as f:
                    self._embeddings_matrix = pickle.load(f)
            except Exception as e:
                print(f"Erro ao carregar embeddings: {e}")
    
    def save_index(self):
        """Salvar índice do conhecimento."""
        data = {
            'sources': [asdict(s) for s in self.sources.values()],
            'total_sources': len(self.sources),
            'last_updated': datetime.now().isoformat()
        }
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Salvar embeddings
        embeddings = self.get_embeddings_matrix()
        with open(self.embeddings_path, 'wb') as f:
            pickle.dump(embeddings, f)
    
    def add_source(self, title: str, content: str, source_type: str, file_path: str = "") -> KnowledgeSource:
        """Adicionar uma nova fonte de conhecimento."""
        source_id = hashlib.md5(f"{title}{datetime.now()}".encode()).hexdigest()[:8]
        
        # Extrair informações automaticamente
        formulas = self.extract_formulas(content)
        numbers = self.extract_numbers(content)
        entities = self.extract_entities(content)
        
        source = KnowledgeSource(
            id=source_id,
            title=title,
            content=content,
            source_type=source_type,
            file_path=file_path,
            uploaded_at=datetime.now().isoformat(),
            metadata={
                'char_count': len(content),
                'word_count': len(content.split()),
                'formula_count': len(formulas),
                'number_count': len(numbers)
            },
            formulas=formulas,
            numbers=numbers,
            entities=entities
        )
        
        self.sources[source_id] = source
        self._embeddings_matrix = None  # Reset cache
        self.save_index()
        return source
    
    def extract_formulas(self, text: str) -> List[Dict[str, Any]]:
        """Extrair fórmulas matemáticas do texto."""
        formulas = []
        
        # Padrões comuns de fórmulas
        patterns = [
            (r'([A-Za-z]+)\s*=\s*([^=\n]+)', 'equation'),
            (r'(\d+)\s*[x×]\s*(\d+)\s*[=]\s*(\d+)', 'multiplication'),
            (r'([A-Za-z]+)\s*\(([^)]+)\)\s*=\s*([^\n]+)', 'function'),
            (r'(\w+)\s*(\+|\-|\*|\/)\s*(\w+)\s*=\s*(\d+)', 'simple_operation'),
            (r'([A-Za-z])\s*=\s*([A-Za-z0-9\*\^\(\)\+\-\/]+)', 'variable'),
        ]
        
        for pattern, formula_type in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                formulas.append({
                    'type': formula_type,
                    'expression': str(match),
                    'source_text': match if isinstance(match, str) else ' '.join(str(m) for m in match)
                })
        
        # Detectar fórmulas LaTeX
        latex_patterns = re.findall(r'\$[^$]+\$', text)
        for latex in latex_patterns:
            formulas.append({
                'type': 'latex',
                'expression': latex,
                'source_text': latex
            })
        
        return formulas
    
    def extract_numbers(self, text: str) -> List[float]:
        """Extrair números do texto."""
        numbers = []
        pattern = r'\b\d+(?:[.,]\d+)?\b'
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                num = float(match.replace(',', '.'))
                numbers.append(num)
            except ValueError:
                pass
        return numbers
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extrair entidades (nomes, conceitos, unidades)."""
        entities = {
            'units': [],
            'concepts': [],
            'names': []
        }
        
        # Unidades de medida
        unit_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(km|m|cm|mm|kg|g|l|ml|s|min|h)',
            r'(\d+(?:[.,]\d+)?)\s*(metros|quilômetros|centímetros|litros|quilos)'
        ]
        
        for pattern in unit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['units'].append(str(match))
        
        # Conceitos (palavras em maiúsculo ou termos técnicos)
        concept_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        matches = re.findall(concept_pattern, text)
        entities['concepts'] = list(set(matches[:20]))
        
        return entities
    
    def get_embeddings_matrix(self) -> np.ndarray:
        """Gerar matriz de embeddings para todos os documentos."""
        if not self.sources:
            return np.array([])
        
        if self._embeddings_matrix is not None:
            return self._embeddings_matrix
        
        documents = [source.content for source in self.sources.values()]
        self._embeddings_matrix = self.vectorizer.fit_transform(documents).toarray()
        return self._embeddings_matrix
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[KnowledgeSource, float]]:
        """Buscar fontes relevantes para a consulta."""
        if not self.sources:
            return []
        
        # Gerar embedding da consulta
        try:
            query_embedding = self.vectorizer.transform([query]).toarray()
        except Exception:
            self.get_embeddings_matrix()
            query_embedding = self.vectorizer.transform([query]).toarray()
        
        # Calcular similaridade
        embeddings = self.get_embeddings_matrix()
        if embeddings.size == 0:
            return []
        
        similarities = cosine_similarity(query_embedding, embeddings)[0]
        
        # Ordenar por relevância
        scored_sources = []
        for idx, source in enumerate(self.sources.values()):
            scored_sources.append((source, float(similarities[idx])))
        
        scored_sources.sort(key=lambda x: x[1], reverse=True)
        return scored_sources[:top_k]
    
    def query_knowledge(self, query: str) -> QueryContext:
        """Consultar o banco de conhecimento."""
        # Buscar fontes relevantes
        relevant_sources = self.search(query)
        
        # Extrair informações relevantes
        extracted_formulas = []
        extracted_numbers = []
        
        for source, score in relevant_sources:
            if score > 0.1:  # Threshold de relevância
                extracted_formulas.extend(source.formulas)
                extracted_numbers.extend(source.numbers)
        
        return QueryContext(
            query=query,
            relevant_sources=[s for s, _ in relevant_sources],
            extracted_formulas=extracted_formulas,
            extracted_numbers=extracted_numbers,
            timestamp=datetime.now().isoformat()
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas do banco de conhecimento."""
        total_formulas = sum(len(s.formulas) for s in self.sources.values())
        total_numbers = sum(len(s.numbers) for s in self.sources.values())
        
        return {
            'total_sources': len(self.sources),
            'total_characters': sum(s.metadata['char_count'] for s in self.sources.values()),
            'total_formulas': total_formulas,
            'total_numbers': total_numbers,
            'source_types': {
                'text': sum(1 for s in self.sources.values() if s.source_type == 'text'),
                'pdf': sum(1 for s in self.sources.values() if s.source_type == 'pdf'),
                'image': sum(1 for s in self.sources.values() if s.source_type == 'image')
            }
        }
    
    def delete_source(self, source_id: str) -> bool:
        """Deletar uma fonte do conhecimento."""
        if source_id in self.sources:
            del self.sources[source_id]
            self._embeddings_matrix = None
            self.save_index()
            return True
        return False


# Instância global
knowledge_base = KnowledgeBase()


# Teste rápido
if __name__ == "__main__":
    print("=" * 60)
    print("Teste do Knowledge Base")
    print("=" * 60)
    
    # Adicionar fonte de teste
    kb = KnowledgeBase(Path("./test_knowledge"))
    source = kb.add_source(
        "Fórmulas de Física",
        "A lei da gravitação universal: F = G * M * m / r². Onde G = 6.67e-11",
        "text"
    )
    print(f"✓ Fonte adicionada: {source.title}")
    
    # Buscar
    results = kb.search("gravidade")
    print(f"✓ Busca encontrou {len(results)} resultados")
    
    # Estatísticas
    stats = kb.get_statistics()
    print(f"✓ Estatísticas: {stats['total_sources']} fontes, {stats['total_formulas']} fórmulas")
    
    print("=" * 60)