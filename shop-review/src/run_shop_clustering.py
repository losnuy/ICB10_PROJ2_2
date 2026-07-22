"""
쇼핑몰 리뷰 데이터(shop-review.csv) 군집화, 실루엣 분석, 상위/하위 키워드 추출 및 지도학습 랜덤 포레스트 분석 모듈입니다.

주요 기능:
1. PART 1: title과 content 결합 기준 TF-IDF 벡터화, KMeans(k=4) 군집화, 실루엣 분석, 상위 30개 및 하위 50개 키워드 시각화
2. PART 2: title + content + product 통합 결합 기준 TF-IDF 벡터화, KMeans(k=4) 군집화, 실루엣 분석, 키워드/교차표 시각화
3. 각 군집별 유의미한(non-zero) 하위 50개 롱테일 키워드(Bottom 50 Keywords) 추출 및 시각화
4. 지도학습 RandomForestClassifier 기반 군집 결정 핵심 피처 중요도 상위 30개 추출 및 시각화
5. 종합 요약 JSON 데이터(clustering_summary.json) 저장
"""
import os
import re
import html
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import koreanize_matplotlib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score, accuracy_score
from sklearn.ensemble import RandomForestClassifier
import matplotlib.cm as cm

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # HTML 엔티티 복원
    text = html.unescape(text)
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', ' ', text)
    # 기호 및 불필요 공백 정제 (한글, 영문, 숫자 외 공백으로)
    text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text)
    # 연속 공백 하나로
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def run_clustering_pipeline(df, text_column, prefix, images_dir, n_clusters=4):
    print(f"\n==========================================")
    print(f"Running clustering pipeline for: {prefix} (col: {text_column})")
    print(f"==========================================")

    # 1. TF-IDF 벡터화
    tfidf = TfidfVectorizer(
        max_features=5000,
        min_df=2,
        ngram_range=(1, 2)
    )
    X_tfidf = tfidf.fit_transform(df[text_column])
    feature_names = np.array(tfidf.get_feature_names_out())
    print(f"TF-IDF Matrix shape: {X_tfidf.shape}")

    # 2. 2차원 차원축소 (TruncatedSVD)
    svd = TruncatedSVD(n_components=2, random_state=42)
    X_2d = svd.fit_transform(X_tfidf)
    print(f"SVD Explained Variance Ratio: {svd.explained_variance_ratio_.sum():.4f}")

    # 3. K-Means 군집화 (k=4)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_tfidf)

    # 4. 실루엣 분석
    silhouette_avg = silhouette_score(X_tfidf, cluster_labels)
    sample_silhouette_values = silhouette_samples(X_tfidf, cluster_labels)
    print(f"Overall Silhouette Score: {silhouette_avg:.4f}")

    # 4.1 실루엣 분석 & 2차원 축소 산점도 시각화
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    ax1.set_xlim([-0.1, 1])
    ax1.set_ylim([0, len(df) + (n_clusters + 1) * 10])

    y_lower = 10
    colors = cm.nipy_spectral(np.linspace(0, 1, n_clusters))

    cluster_silhouette_means = {}
    for i in range(n_clusters):
        ith_cluster_silhouette_values = sample_silhouette_values[cluster_labels == i]
        ith_cluster_silhouette_values.sort()

        size_cluster_i = ith_cluster_silhouette_values.shape[0]
        y_upper = y_lower + size_cluster_i

        color = colors[i]
        ax1.fill_betweenx(
            np.arange(y_lower, y_upper),
            0,
            ith_cluster_silhouette_values,
            facecolor=color,
            edgecolor=color,
            alpha=0.7
        )
        ax1.text(-0.05, y_lower + 0.5 * size_cluster_i, f"군집 {i}")
        y_lower = y_upper + 10

        cluster_silhouette_means[i] = float(np.mean(ith_cluster_silhouette_values))

    title_prefix = "PRODUCT 포함" if "with_product" in prefix else "기존 (PRODUCT 미포함)"
    ax1.set_title(f"[{title_prefix}] 군집별 실루엣 계수 다이어그램 (k=4)", fontsize=14, fontweight='bold')
    ax1.set_xlabel("실루엣 계수 (Silhouette Coefficient Value)", fontsize=12)
    ax1.set_ylabel("군집 (Cluster)", fontsize=12)
    ax1.axvline(x=silhouette_avg, color="red", linestyle="--", label=f"평균 실루엣 점수 ({silhouette_avg:.4f})")
    ax1.legend(loc="upper right")

    # 2D Scatter plot
    for i in range(n_clusters):
        cluster_mask = (cluster_labels == i)
        ax2.scatter(
            X_2d[cluster_mask, 0],
            X_2d[cluster_mask, 1],
            s=15,
            color=colors[i],
            alpha=0.6,
            label=f"군집 {i} (n={cluster_mask.sum()})"
        )

    centroids_2d = np.array([X_2d[cluster_labels == i].mean(axis=0) for i in range(n_clusters)])
    ax2.scatter(
        centroids_2d[:, 0],
        centroids_2d[:, 1],
        marker='X',
        s=200,
        linewidths=2,
        color='black',
        zorder=10,
        label='군집 중심점 (Centroids)'
    )

    ax2.set_title(f"[{title_prefix}] 2차원 차원축소 (TruncatedSVD) 군집 산점도", fontsize=14, fontweight='bold')
    ax2.set_xlabel("SVD 차원 1", fontsize=12)
    ax2.set_ylabel("SVD 차원 2", fontsize=12)
    ax2.legend(loc="upper right")

    plt.tight_layout()
    silhouette_img_filename = f"{prefix}_silhouette_analysis.png" if "with_product" in prefix else "silhouette_analysis.png"
    silhouette_img_path = os.path.join(images_dir, silhouette_img_filename)
    plt.savefig(silhouette_img_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {silhouette_img_path}")

    # 5. 각 군집별 상위 30개 및 하위 50개 키워드 추출 & 시각화
    cluster_top_keywords = {}
    cluster_bottom_keywords = {}

    for i in range(n_clusters):
        cluster_indices = np.where(cluster_labels == i)[0]
        cluster_tfidf_mean = np.mean(X_tfidf[cluster_indices].toarray(), axis=0)
        
        # 5.1 상위 30개 키워드
        top30_idx = np.argsort(cluster_tfidf_mean)[::-1][:30]
        top30_words = feature_names[top30_idx]
        top30_scores = cluster_tfidf_mean[top30_idx]

        kw_list = [{"word": str(w), "score": round(float(s), 5)} for w, s in zip(top30_words, top30_scores)]
        cluster_top_keywords[i] = kw_list

        plt.figure(figsize=(12, 8))
        y_pos = np.arange(len(top30_words))
        plt.barh(y_pos, top30_scores[::-1], align='center', color=colors[i], alpha=0.85)
        plt.yticks(y_pos, top30_words[::-1], fontsize=11)
        plt.xlabel('평균 TF-IDF 점수', fontsize=12)
        plt.title(f'[{title_prefix}] 군집 {i} 상위 30개 키워드 (샘플 수: {len(cluster_indices)}개)', fontsize=14, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        kw_img_filename = f"{prefix}_cluster_{i}_keywords.png" if "with_product" in prefix else f"cluster_{i}_keywords.png"
        kw_img_path = os.path.join(images_dir, kw_img_filename)
        plt.savefig(kw_img_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {kw_img_path}")

        # 5.2 하위 50개 키워드 (non-zero 기준)
        nonzero_mask = (cluster_tfidf_mean > 0)
        nonzero_indices = np.where(nonzero_mask)[0]
        nonzero_scores = cluster_tfidf_mean[nonzero_indices]
        
        # 점수가 오름차순으로 하위 50개 (만약 non-zero 어휘가 50개 미만이면 전체 추출)
        bottom50_sorted_order = np.argsort(nonzero_scores)[:50]
        bottom50_idx = nonzero_indices[bottom50_sorted_order]
        bottom50_words = feature_names[bottom50_idx]
        bottom50_scores = cluster_tfidf_mean[bottom50_idx]

        b_kw_list = [{"word": str(w), "score": round(float(s), 6)} for w, s in zip(bottom50_words, bottom50_scores)]
        cluster_bottom_keywords[i] = b_kw_list

        plt.figure(figsize=(12, 12))
        y_pos_b = np.arange(len(bottom50_words))
        plt.barh(y_pos_b, bottom50_scores, align='center', color='gray', alpha=0.75)
        plt.yticks(y_pos_b, bottom50_words, fontsize=9)
        plt.xlabel('평균 TF-IDF 점수 (하위 롱테일 어휘)', fontsize=12)
        plt.title(f'[{title_prefix}] 군집 {i} 하위 50개 키워드 (Bottom 50 Keywords)', fontsize=14, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.tight_layout()

        b_kw_img_filename = f"{prefix}_cluster_{i}_bottom50_keywords.png" if "with_product" in prefix else f"cluster_{i}_bottom50_keywords.png"
        b_kw_img_path = os.path.join(images_dir, b_kw_img_filename)
        plt.savefig(b_kw_img_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved Bottom 50 Plot: {b_kw_img_path}")

    # 6. 군집 결과 x PRODUCT 컬럼 교차표 시각화
    crosstab_counts = pd.crosstab(cluster_labels, df['product'])
    crosstab_norm = pd.crosstab(cluster_labels, df['product'], normalize='index') * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    sns.heatmap(crosstab_counts, annot=True, fmt='d', cmap='YlGnBu', ax=ax1, cbar=True)
    ax1.set_title(f'[{title_prefix}] 군집 - PRODUCT 빈도 교차표', fontsize=14, fontweight='bold')
    ax1.set_xlabel('PRODUCT 컬럼', fontsize=12)
    ax1.set_ylabel('군집 (Cluster)', fontsize=12)
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    crosstab_norm.plot(kind='bar', stacked=True, colormap='tab10', ax=ax2, alpha=0.85)
    ax2.set_title(f'[{title_prefix}] 군집별 PRODUCT 구성 비율 (%)', fontsize=14, fontweight='bold')
    ax2.set_xlabel('군집 (Cluster)', fontsize=12)
    ax2.set_ylabel('비율 (%)', fontsize=12)
    ax2.legend(title='PRODUCT', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.setp(ax2.get_xticklabels(), rotation=0)

    plt.tight_layout()
    crosstab_img_filename = f"{prefix}_crosstab.png" if "with_product" in prefix else "cluster_product_crosstab.png"
    crosstab_img_path = os.path.join(images_dir, crosstab_img_filename)
    plt.savefig(crosstab_img_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {crosstab_img_path}")

    # 7. 지도학습 랜덤 포레스트 피처 중요도 분석
    print("\nTraining RandomForestClassifier for feature importance...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_tfidf, cluster_labels)
    y_pred = rf.predict(X_tfidf)
    rf_acc = accuracy_score(cluster_labels, y_pred)
    print(f"RandomForest Training Accuracy: {rf_acc:.4f}")

    importances = rf.feature_importances_
    rf_top30_idx = np.argsort(importances)[::-1][:30]
    rf_top30_words = feature_names[rf_top30_idx]
    rf_top30_scores = importances[rf_top30_idx]

    rf_top_keywords = [{"word": str(w), "importance": round(float(s), 5)} for w, s in zip(rf_top30_words, rf_top30_scores)]

    plt.figure(figsize=(12, 8))
    y_pos = np.arange(len(rf_top30_words))
    plt.barh(y_pos, rf_top30_scores[::-1], align='center', color='teal', alpha=0.85)
    plt.yticks(y_pos, rf_top30_words[::-1], fontsize=11)
    plt.xlabel('피처 중요도 (Mean Decrease in Impurity)', fontsize=12)
    plt.title(f'[{title_prefix}] 랜덤 포레스트 지도학습 피처 중요도 상위 30개 어휘 (학습 정확도: {rf_acc*100:.2f}%)', fontsize=14, fontweight='bold')
    plt.gca().invert_yaxis()
    plt.tight_layout()

    rf_img_filename = f"rf_feature_importance_{prefix}.png"
    rf_img_path = os.path.join(images_dir, rf_img_filename)
    plt.savefig(rf_img_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved RF Feature Importance Plot: {rf_img_path}")

    cluster_counts_dict = pd.Series(cluster_labels).value_counts().sort_index().to_dict()

    return {
        "overall_silhouette_score": round(float(silhouette_avg), 4),
        "cluster_silhouette_means": {k: round(v, 4) for k, v in cluster_silhouette_means.items()},
        "cluster_counts": {int(k): int(v) for k, v in cluster_counts_dict.items()},
        "cluster_top_keywords": cluster_top_keywords,
        "cluster_bottom_keywords": cluster_bottom_keywords,
        "crosstab_counts": {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in crosstab_counts.to_dict().items()},
        "crosstab_norm": {str(k): {str(k2): float(v2) for k2, v2 in v.items()} for k, v in crosstab_norm.round(2).to_dict().items()},
        "rf_accuracy": round(float(rf_acc), 4),
        "rf_top_feature_importances": rf_top_keywords
    }

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'shop-review.csv')
    images_dir = os.path.join(base_dir, 'images')
    report_dir = os.path.join(base_dir, 'report')

    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)

    # 전처리
    df['clean_title'] = df['title'].apply(clean_text)
    df['clean_content'] = df['content'].apply(clean_text)
    df['clean_product'] = df['product'].apply(clean_text)

    df['full_text'] = df['clean_title'] + ' ' + df['clean_content']
    df['full_text_with_product'] = df['clean_title'] + ' ' + df['clean_content'] + ' ' + df['clean_product']

    # PART 1: PRODUCT 미포함 군집화 및 상위 30개 / 하위 50개 키워드 추출
    part1_res = run_clustering_pipeline(df, 'full_text', 'part1', images_dir)

    # PART 2: PRODUCT 포함 군집화 및 상위 30개 / 하위 50개 키워드 추출
    part2_res = run_clustering_pipeline(df, 'full_text_with_product', 'with_product', images_dir)

    # JSON 통합 저장
    summary_data = {
        "total_rows": int(len(df)),
        "total_cols": int(df.shape[1]),
        "part1_without_product": part1_res,
        "part2_with_product": part2_res,
        "product_counts": {str(k): int(v) for k, v in df['product'].value_counts().to_dict().items()}
    }

    summary_json_path = os.path.join(report_dir, 'clustering_summary.json')
    with open(summary_json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"\nSummary JSON saved to {summary_json_path}")
    print("All clustering pipelines with Top 30 and Bottom 50 keywords completed successfully!")

if __name__ == '__main__':
    main()
