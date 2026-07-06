<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">{{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.title') }}</h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Backlog Context -->
            <div class="context-block">
              <div class="context-item">
                <div class="context-label">{{ t('purchaseOrder.orderId') }}</div>
                <div class="context-value order-id">{{ backlogItem.order_id }}</div>
              </div>
              <div class="context-item">
                <div class="context-label">{{ t('purchaseOrder.sku') }}</div>
                <div class="context-value sku">{{ backlogItem.item_sku }}</div>
              </div>
              <div class="context-item">
                <div class="context-label">{{ t('purchaseOrder.itemName') }}</div>
                <div class="context-value">{{ translateProductName(backlogItem.item_name) }}</div>
              </div>
              <div class="context-item">
                <div class="context-label">{{ t('purchaseOrder.shortage') }}</div>
                <div class="context-value shortage">{{ shortage }}</div>
              </div>
            </div>

            <div class="context-divider"></div>

            <!-- Create Mode -->
            <div v-if="mode === 'create'" class="po-form">
              <div v-if="createError" class="form-error">{{ createError }}</div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label for="po-supplier">{{ t('purchaseOrder.supplier') }}</label>
                  <input
                    id="po-supplier"
                    v-model="formData.supplier_name"
                    type="text"
                    class="po-input"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                  <input
                    id="po-quantity"
                    v-model.number="formData.quantity"
                    type="number"
                    min="1"
                    class="po-input"
                  />
                </div>

                <div class="form-group">
                  <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }}</label>
                  <input
                    id="po-unit-cost"
                    v-model.number="formData.unit_cost"
                    type="number"
                    min="0"
                    step="0.01"
                    class="po-input"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label for="po-expected-delivery">{{ t('purchaseOrder.expectedDelivery') }}</label>
                  <input
                    id="po-expected-delivery"
                    v-model="formData.expected_delivery_date"
                    type="date"
                    class="po-input"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group flex-1">
                  <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                  <textarea
                    id="po-notes"
                    v-model="formData.notes"
                    class="po-textarea"
                    rows="3"
                  ></textarea>
                </div>
              </div>

              <div class="total-cost-row">
                <span class="total-cost-label">{{ t('purchaseOrder.totalCost') }}</span>
                <span class="total-cost-value">{{ currencySymbol }}{{ totalCost.toFixed(2) }}</span>
              </div>
            </div>

            <!-- View Mode -->
            <div v-else class="po-view">
              <div v-if="viewLoading" class="view-status">{{ t('common.loading') }}</div>
              <div v-else-if="viewError" class="form-error">{{ viewError }}</div>
              <div v-else-if="viewData" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                  <div class="info-value">{{ viewData.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ viewData.quantity }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ currencySymbol }}{{ Number(viewData.unit_cost).toFixed(2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.totalCost') }}</div>
                  <div class="info-value">{{ currencySymbol }}{{ (viewData.quantity * viewData.unit_cost).toFixed(2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ formatDate(viewData.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value">
                    <span class="badge">{{ viewData.status }}</span>
                  </div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDate(viewData.created_date) }}</div>
                </div>
                <div v-if="viewData.notes" class="info-item flex-1">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value">{{ viewData.notes }}</div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">
              {{ mode === 'create' ? t('purchaseOrder.cancel') : t('purchaseOrder.close') }}
            </button>
            <button
              v-if="mode === 'create'"
              class="btn-primary"
              :disabled="!isFormValid || submitting"
              @click="handleSubmit"
            >
              {{ submitting ? t('purchaseOrder.creating') : t('purchaseOrder.create') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  backlogItem: {
    type: Object,
    default: null
  },
  mode: {
    type: String,
    default: 'create'
  }
})

const emit = defineEmits(['close', 'po-created'])

const submitting = ref(false)
const createError = ref(null)

const viewLoading = ref(false)
const viewError = ref(null)
const viewData = ref(null)

const formData = ref({
  supplier_name: '',
  quantity: 1,
  unit_cost: '',
  expected_delivery_date: '',
  notes: ''
})

const shortage = computed(() => {
  if (!props.backlogItem) return 0
  return props.backlogItem.quantity_needed - props.backlogItem.quantity_available
})

const currencySymbol = computed(() => currentCurrency.value === 'JPY' ? '¥' : '$')

const totalCost = computed(() => {
  const quantity = Number(formData.value.quantity) || 0
  const unitCost = Number(formData.value.unit_cost) || 0
  return quantity * unitCost
})

const isFormValid = computed(() => {
  return !!formData.value.supplier_name.trim() &&
    Number(formData.value.quantity) > 0 &&
    formData.value.unit_cost !== '' &&
    Number(formData.value.unit_cost) >= 0 &&
    !!formData.value.expected_delivery_date
})

const resetForm = () => {
  formData.value = {
    supplier_name: '',
    quantity: shortage.value > 0 ? shortage.value : 1,
    unit_cost: '',
    expected_delivery_date: '',
    notes: ''
  }
  createError.value = null
  submitting.value = false
}

const fetchPurchaseOrder = async () => {
  if (!props.backlogItem) return
  const requestedId = props.backlogItem.id
  viewLoading.value = true
  viewError.value = null
  viewData.value = null
  try {
    const result = await api.getPurchaseOrderByBacklogItem(requestedId)
    if (props.backlogItem?.id !== requestedId) return
    viewData.value = result
  } catch (err) {
    if (props.backlogItem?.id !== requestedId) return
    const detail = err.response?.data?.detail
    viewError.value = typeof detail === 'string' ? detail : t('purchaseOrder.loadError')
  } finally {
    viewLoading.value = false
  }
}

watch(() => [props.isOpen, props.mode], ([isOpen, mode]) => {
  if (!isOpen) return
  resetForm()
  viewError.value = null
  viewData.value = null
  if (mode === 'view') {
    fetchPurchaseOrder()
  }
})

const close = () => {
  emit('close')
}

const handleSubmit = async () => {
  if (!isFormValid.value || submitting.value || !props.backlogItem) return
  submitting.value = true
  createError.value = null
  try {
    const payload = {
      backlog_item_id: props.backlogItem.id,
      supplier_name: formData.value.supplier_name.trim(),
      quantity: Number(formData.value.quantity),
      unit_cost: Number(formData.value.unit_cost),
      expected_delivery_date: formData.value.expected_delivery_date,
      notes: formData.value.notes.trim()
    }
    const response = await api.createPurchaseOrder(payload)
    emit('po-created', response)
  } catch (err) {
    const detail = err.response?.data?.detail
    createError.value = typeof detail === 'string' ? detail : t('purchaseOrder.createError')
  } finally {
    submitting.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
  return date.toLocaleDateString(locale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC'
  })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.context-block {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.25rem;
}

.context-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.context-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.context-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.context-value.order-id,
.context-value.sku {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

.context-value.shortage {
  color: #dc2626;
  font-weight: 700;
}

.context-divider {
  height: 1px;
  background: #e2e8f0;
  margin: 1.5rem 0;
}

.form-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.po-form {
  display: flex;
  flex-direction: column;
}

.form-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-row:last-of-type {
  margin-bottom: 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.form-group.flex-1 {
  flex: 1;
}

label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
}

.po-input,
.po-textarea {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: border-color 0.2s ease;
  font-family: inherit;
}

.po-textarea {
  resize: vertical;
}

.po-input:focus,
.po-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.total-cost-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1.5rem;
  padding: 1rem 1.25rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.total-cost-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.total-cost-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

.view-status {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item.flex-1 {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: capitalize;
  background: #dbeafe;
  color: #1e40af;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.btn-primary {
  padding: 0.625rem 1.25rem;
  background: #2563eb;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
