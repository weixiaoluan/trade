"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function DisclaimerPage() {
  return (
    <div className="min-h-screen bg-[#020617] py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* 返回按钮 */}
        <Link 
          href="/login" 
          className="inline-flex items-center gap-2 text-slate-400 hover:text-slate-300 mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>返回</span>
        </Link>

        <div className="bg-white/[0.03] backdrop-blur-xl rounded-2xl border border-white/[0.08] p-6 sm:p-8">
          <h1 className="text-2xl font-bold text-slate-100 mb-6 text-center">
            用户协议与免责声明
          </h1>

          <div className="space-y-6 text-slate-400 text-sm leading-relaxed">
            {/* 工具性质说明 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">一、工具性质说明</h2>
              <div className="space-y-2 pl-4 border-l-2 border-indigo-500/30">
                <p>1. 本工具是个人开发的证券数据研究学习工具，仅供个人学习、研究和技术交流使用。</p>
                <p>2. 本工具不是证券投资咨询机构，不具备证券投资咨询业务资格，不提供任何形式的证券投资咨询服务。</p>
                <p>3. 本工具所有功能均为技术指标计算、数据可视化和信息整理，属于数据处理工具范畴。</p>
              </div>
            </section>

            {/* 数据来源说明 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">二、数据来源说明</h2>
              <div className="space-y-2 pl-4 border-l-2 border-indigo-500/30">
                <p>1. 本工具使用的所有数据均来自公开渠道，包括但不限于 Yahoo Finance、东方财富等公开数据接口。</p>
                <p>2. 数据仅供参考，本工具不对数据的准确性、完整性、及时性作任何保证。</p>
                <p>3. 技术指标计算结果基于历史数据，不代表未来走势。</p>
              </div>
            </section>

            {/* AI分析说明 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">三、AI分析内容说明</h2>
              <div className="space-y-2 pl-4 border-l-2 border-indigo-500/30">
                <p>1. 本工具中的"AI分析"、"研报"等内容均由人工智能模型基于公开数据和技术指标自动生成。</p>
                <p>2. AI生成的所有内容仅为技术分析结果的文字化呈现，不代表任何投资观点或建议。</p>
                <p>3. AI模型可能存在错误、偏差或幻觉，生成内容仅供学习参考，不应作为投资决策依据。</p>
                <p>4. 所谓"参考价位"、"技术评级"等均为基于技术指标的数学计算结果，不构成买卖建议。</p>
              </div>
            </section>

            {/* 风险提示 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">四、风险提示</h2>
              <div className="space-y-2 pl-4 border-l-2 border-rose-500/30 bg-rose-500/5 p-4 rounded-r-lg">
                <p className="text-rose-300">⚠️ 证券投资具有高风险性，可能导致本金损失。</p>
                <p>1. 本工具的任何内容均不构成投资建议、推荐、指导或承诺。</p>
                <p>2. 用户不应将本工具的任何输出作为投资决策的依据。</p>
                <p>3. 任何投资决策应咨询持有合法资质的专业投资顾问。</p>
                <p>4. 用户因使用本工具而产生的任何投资损失，本工具概不负责。</p>
              </div>
            </section>

            {/* 使用条款 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">五、使用条款</h2>
              <div className="space-y-2 pl-4 border-l-2 border-indigo-500/30">
                <p>1. 用户注册并使用本工具，即表示已阅读、理解并同意本协议全部内容。</p>
                <p>2. 本工具仅限个人学习研究使用，禁止用于商业用途或向他人提供投资咨询服务。</p>
                <p>3. 用户应遵守所在地区的法律法规，合法合规使用本工具。</p>
                <p>4. 本工具保留随时修改本协议的权利，修改后的协议一经发布即生效。</p>
              </div>
            </section>

            {/* 知识产权 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">六、知识产权</h2>
              <div className="space-y-2 pl-4 border-l-2 border-indigo-500/30">
                <p>1. 本工具的代码、界面设计等知识产权归开发者所有。</p>
                <p>2. 用户生成的分析报告仅供个人使用，不得用于商业传播。</p>
              </div>
            </section>

            {/* 联系方式 */}
            <section>
              <h2 className="text-lg font-semibold text-slate-200 mb-3">七、其他</h2>
              <div className="space-y-2 pl-4 border-l-2 border-indigo-500/30">
                <p>1. 本协议的解释权归本工具开发者所有。</p>
                <p>2. 如有任何争议，应友好协商解决。</p>
              </div>
            </section>
          </div>

          {/* 确认按钮 */}
          <div className="mt-8 text-center">
            <Link
              href="/login"
              className="inline-block px-8 py-3 bg-indigo-500 hover:bg-indigo-600 text-white rounded-xl transition-colors"
            >
              我已阅读并理解
            </Link>
          </div>

          <p className="text-center text-slate-600 text-xs mt-6">
            最后更新：2026年1月
          </p>
        </div>
      </div>
    </div>
  );
}
