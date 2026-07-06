<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card">
      <div class="budget-control">
        <label class="budget-label" for="budget-slider">{{ t('restocking.budgetLabel') }}</label>
        <input
          id="budget-slider"
          type="range"
          min="0"
          max="100000"
          step="1000"
          v-model.number="budget"
          class="budget-slider"
        />
        <span class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="recommendations">
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.budget') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ recommendations.budget.toLocaleString() }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.plannedSpend') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ recommendations.total_cost.toLocaleString() }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.summary.remaining') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ recommendations.remaining_budget.toLocaleString() }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.itemsSelected') }}</div>
          <div class="stat-value">{{ recommendations.items.length }}</div>
        </div>
      </div>

      <div v-if="placedOrder" class="success-banner">
        <strong>
          {{ t('restocking.orderSuccess', { orderNumber: placedOrder.order_number, days: placedOrder.lead_time_days }) }}
        </strong>
        <router-link to="/orders" class="view-orders-link">{{ t('restocking.viewOrders') }}</router-link>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendationsTitle') }} ({{ recommendations.items.length }})</h3>
          <button
            class="btn-primary"
            :disabled="placing || recommendations.items.length === 0"
            @click="placeOrder"
          >
            {{ placing ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>
        <div v-if="recommendations.items.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.rank') }}</th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.currentDemand') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.gap') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.estimatedCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in recommendations.items" :key="item.sku">
                <td>{{ index + 1 }}</td>
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td>{{ item.current_demand.toLocaleString() }}</td>
                <td>{{ item.forecasted_demand.toLocaleString() }}</td>
                <td>{{ item.demand_gap.toLocaleString() }}</td>
                <td><strong>{{ item.recommended_quantity.toLocaleString() }}</strong></td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toLocaleString() }}</td>
                <td><strong>{{ currencySymbol }}{{ item.estimated_cost.toLocaleString() }}</strong></td>
                <td>{{ item.lead_time_days }} {{ t('orders.days') }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const budget = ref(20000)
    const recommendations = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const placing = ref(false)
    const placedOrder = ref(null)

    const loadRecommendations = async () => {
      try {
        error.value = null
        recommendations.value = await api.getRestockRecommendations(budget.value)
      } catch (err) {
        error.value = t('restocking.loadError') + ': ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Debounce slider input so dragging doesn't fire a request per step
    let debounceTimer = null
    watch(budget, () => {
      placedOrder.value = null
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 250)
    })
    onUnmounted(() => clearTimeout(debounceTimer))

    const placeOrder = async () => {
      try {
        placing.value = true
        error.value = null
        placedOrder.value = await api.createRestockOrder({
          items: recommendations.value.items.map(item => ({
            sku: item.sku,
            quantity: item.recommended_quantity
          }))
        })
      } catch (err) {
        error.value = t('restocking.placeError') + ': ' + err.message
      } finally {
        placing.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      budget,
      recommendations,
      loading,
      error,
      placing,
      placedOrder,
      placeOrder,
      currencySymbol,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-control {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}

.budget-slider {
  flex: 1;
  accent-color: #3b82f6;
  cursor: pointer;
}

.budget-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 110px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.success-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}

.view-orders-link {
  color: #065f46;
  font-weight: 600;
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: 2.5rem;
  color: #64748b;
  font-size: 0.938rem;
}
</style>
