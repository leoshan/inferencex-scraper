"""
应用场景聚类分析
"""

import logging
import pandas as pd
from typing import Dict

logger = logging.getLogger(__name__)


class AppClusterAnalyzer:
    """应用场景聚类分析"""

    def cluster_by_usage_pattern(
        self,
        app_data: pd.DataFrame
    ) -> Dict:
        """基于使用模式聚类应用"""
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
        except ImportError:
            logger.warning("sklearn not installed, skipping clustering")
            return {'clusters': {}, 'labels': {}}

        features = []
        app_names = []

        for app_name in app_data['app_name'].unique():
            app_df = app_data[app_data['app_name'] == app_name]

            total = app_df['total_tokens'].sum()
            if total == 0:
                continue

            feature_vector = app_df.groupby('model_slug')['total_tokens'].sum() / total
            features.append(feature_vector.fillna(0))
            app_names.append(app_name)

        if len(features) < 3:
            return {'clusters': {}, 'labels': {}}

        feature_df = pd.DataFrame(features).fillna(0)
        scaler = StandardScaler()
        X = scaler.fit_transform(feature_df)

        n_clusters = min(5, len(features) // 2)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(X)

        clusters = {}
        for i, label in enumerate(labels):
            label_key = int(label)  # 转换为 Python int
            if label_key not in clusters:
                clusters[label_key] = []
            clusters[label_key].append(app_names[i])

        cluster_labels = self._generate_cluster_labels(clusters, app_data)

        return {
            'clusters': clusters,
            'labels': cluster_labels
        }

    def _generate_cluster_labels(
        self,
        clusters: Dict,
        app_data: pd.DataFrame
    ) -> Dict:
        """生成聚类标签"""
        labels = {}

        for cluster_id, apps in clusters.items():
            cluster_data = app_data[app_data['app_name'].isin(apps)]

            top_models = cluster_data.groupby('model_slug')['total_tokens'].sum() \
                .nlargest(3).index.tolist()

            labels[cluster_id] = {
                'name': f"Cluster {cluster_id}",
                'top_models': top_models,
                'app_count': len(apps)
            }

        return labels
