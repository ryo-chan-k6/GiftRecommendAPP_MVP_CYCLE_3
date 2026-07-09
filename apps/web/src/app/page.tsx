import { Button } from "@/components/action/Button";
import { Container } from "@/components/layout/Container";
import { Heading } from "@/components/display/Heading";
import { Text } from "@/components/display/Text";

/** Phase4a W2 起動確認用プレースホルダー（Phase4b 画面実装は out of scope） */
export default function HomePage() {
  return (
    <main>
      <Container className="py-12">
        <Heading level={1}>Gift Recommendation Service</Heading>
        <Text className="mt-4 text-text-secondary">
          web-foundation 共通 UI コンポーネント骨格（Issue #728）
        </Text>
        <div className="mt-8">
          <Button variant="primary" size="lg">
            レコメンドを始める
          </Button>
        </div>
      </Container>
    </main>
  );
}
